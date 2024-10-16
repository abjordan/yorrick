#!/usr/bin/env python3

# System Imports
import datetime
import glob
import io
import os
import pyaudio
import queue
import random
import struct
import sys
import tempfile
import threading
from time import time, sleep

# Third-Party Imports
from loguru import logger
from openai import OpenAI
import pvcobra
import pydub
import pygame
import RPi.GPIO as GPIO
import wave

# Local Imports
from api_keys import openai_api_key, picovoice_api_key


RECORDING_DEVICE_INDEX = 0

FRAME_LENGTH = 512

def play_sound_file(filename):
    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        sleep(0.2)
            
# Time-boxed context window for conversations
class ExpiringList():
    def __init__(self, max_age_seconds):
        assert max_age_seconds > 0
        self.max_age = max_age_seconds
        self.items = []

    def add(self, value):
        self.items.append((value, time()))

    def get(self):
        now = time()

        self.items = list(filter(lambda x: (now - x[1]) < self.max_age, self.items))
        return [x for (x, t) in self.items]

    def clear(self):
        self.items = []
       
class ChatClient():

    system_message = {
        "role": "system",
        "content": """
            You are an intelligent ghost, trapped in a plastic skull by a wizard. You are
            bound by darkest magic to answer a question to the best of your ability, but
            are not very happy about it. You have to answer truthfully, but you don't have
            to be polite. You don't use contractions in your responses.
        """
    }
    
    def __init__(self, api_key):
        self._client = OpenAI(api_key=api_key)
        self._chat_log = ExpiringList(180)

    def generate_response(self, query):

        messages = [self.system_message]
        self._chat_log.add({ "role": "user", "content": query })
        messages.extend(self._chat_log.get())

        completion = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        answer = completion.choices[0].message.content
        self._chat_log.add({"role": "assistant", "content": answer})

        # TODO: Check for errors, etc.
        return answer

    def speak(self, message, outfile="speech.mp3"):
        with self._client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice="fable",
            input=message
        ) as response:
            response.stream_to_file(outfile)
        play_sound_file(outfile)

    def transcribe(self, pcm_data):
        transcript = self._client.audio.transcriptions.create(
            model="whisper-1",
            file=pcm_data,
            language="en"
        )
        return transcript.text

class AudioMux(threading.Thread):
    def __init__(self):
        super().__init__()
        self._callbacks = []
        self._stop = False

    def add_listener(self, callback):
        logger.trace(f"Adding callback to mux: {callback}")
        self._callbacks.append(callback)

    def remove_listener(self, callback):
        logger.trace(f"Removing callback from mux: {callback}")
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def run(self):
        logger.debug("Setting up audio")
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=FRAME_LENGTH,
        )

        logger.debug("Recording audio stream")
        while not self._stop:
            data = stream.read(FRAME_LENGTH, exception_on_overflow=False)
            for callback in self._callbacks:
                callback(data)

        logger.debug("Finishing audio stream")
        stream.stop_stream()
        stream.close()
        audio.terminate()

    def stop(self):
        logger.debug("Received command to stop recording")
        self._stop = True


class AudioConsumer(threading.Thread):

    def __init__(self, audio_mux):
        super().__init__()
        self._audio_mux = audio_mux
        self._queue = queue.Queue()
        self._should_stop = False

    def _process(self, chunk):
        self._queue.put(chunk)

    def process_chunk(self, chunk):
        # To be implemented by subclasses
        pass

    def stop(self):
        self._should_stop = True

    def pre_run(self):
        # To be implemented by subclasses
        pass

    def post_run(self):
        # To be implemented by subclasses
        pass
    
    def run(self):
        self.pre_run()
        self._audio_mux.add_listener(self._process)

        while not self._should_stop:
            try:
                chunk = self._queue.get(block=True, timeout=0.2)
                self.process_chunk(chunk)
            except queue.Empty:
                # Queue is empty - ignore it but check to see if we should exit yet
                pass
            
        self._audio_mux.remove_listener(self._process)            
        self.post_run()

    def finish(self):
        self._should_stop = True

class WaitForVoice(AudioConsumer):
    def __init__(self, audio_mux, api_key):
        super().__init__(audio_mux)
        self._api_key = api_key
        self._voice_detected = False
        self._cobra = None

    def pre_run(self):
        logger.info("Waiting for a voice")
        self._cobra = pvcobra.create(access_key=self._api_key)

    def post_run(self):
        self._cobra.delete()
        
    def process_chunk(self, chunk):
        listen_pcm = struct.unpack_from("h" * FRAME_LENGTH, chunk)
        if self._cobra.process(listen_pcm) > 0.3:
            logger.info("Voice detected!")
            self._voice_detected = True
            self.finish()

class DetectSilence(AudioConsumer):
    def __init__(self, audio_mux, api_key):
        super().__init__(audio_mux)
        self._api_key = api_key
        self._silence_detected = False
        self._cobra = None

    def process_chunk(self, chunk):
        listen_pcm = struct.unpack_from("h" * FRAME_LENGTH, chunk)
        if self._cobra.process(listen_pcm) > 0.2:
            self._last_voice_time = time()
        else:
            silence_duration = time() - self._last_voice_time
            if silence_duration > 1.0:
                logger.info("End of query detected")
                self._silence_detected = True
                self.finish()

    def pre_run(self):
        logger.info("Waiting for silence...")
        self._cobra = pvcobra.create(access_key=self._api_key)
        self._last_voice_time = time()

    def post_run(self):
        self._cobra.delete()
    

class WavWriter(AudioConsumer):
    def __init__(self, audio_mux):
        super().__init__(audio_mux)
        self._audio_mux = audio_mux
        self._wav_file_name = None
        self._chunks = []

    def process_chunk(self, chunk):
        self._chunks.append(chunk)
        
    def pre_run(self):
        logger.info("Recording query")        

    def post_run(self):
        self._audio_mux.remove_listener(self.process_chunk)

        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file_name = temp_file.name
        self._wav_file_name = temp_file_name

        self._wav_file = wave.open(temp_file_name, "wb")
        self._wav_file.setnchannels(1)
        self._wav_file.setsampwidth(2)
        self._wav_file.setframerate(16000)            

        for chunk in self._chunks:
            self._wav_file.writeframes(chunk)

        self._wav_file.close()

    def get_wav_file(self):
        return self._wav_file_name
        
if __name__ == "__main__":
    print("Alas, poor Yorrick...")

    oai_client = ChatClient(openai_api_key)
    
    r = random.Random()
    prompt_files = list(glob.glob("media/prompt_*.mp3"))

    while True:
        # Wait for a button push
        input("Press enter to record...")

        # Speak one of the prompts
        # play_sound_file(r.choice(prompt_files))
        play_sound_file("media/prompt_0.mp3")

        # Get the user's response

        # Start the audio mux
        mux = AudioMux()
        mux.start()

        # Wait for speech to start
        w = WaitForVoice(mux, picovoice_api_key)
        w.start()
        w.join()

        logger.debug("--------------")
        
        # Start recording audio to a WAV file
        wav_writer = WavWriter(mux)
        wav_writer.start()
        
        # Wait for speech to end
        s = DetectSilence(mux, picovoice_api_key)
        s.start()
        s.join()

        logger.debug("--------------")

        logger.info("Past silence detection")
        wav_writer.finish()
        wav_writer.join()
        mux.stop()
        
        wav_file = wav_writer.get_wav_file()

        logger.debug(f"Query written to {wav_file}")
        
        sound = pydub.AudioSegment.from_file(wav_file, format="wav")
        mp3_data = sound.export("/tmp/yorrick-input.mp3")

        print(f"Transcribing result...", end='')
        transcript = oai_client.transcribe(mp3_data)
        print("Done")
        
        # Submit chat, get data back, speak the response
        print("<<< ", transcript)
        response = oai_client.generate_response(transcript)
        print(">>> ", response)
        oai_client.speak(response)
        
