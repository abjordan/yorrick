#!/usr/bin/env python3

# System Imports
import datetime
import io
import os
import pyaudio
import random
import struct
import sys
import threading
from time import time, sleep

# Third-Party Imports
from openai import OpenAI
import pygame
import RPi.GPIO as GPIO



# Local Imports
from api_keys import openai_api_key


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

    def speak(self, message):
        response = self._client.audio.speech.create(
            model="tts-1",
            voice="fable",
            input=message
        )

        response.stream_to_file("speech.mp3")

        pygame.mixer.init()
        pygame.mixer.music.load("speech.mp3")
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            sleep(0.2)

    
if __name__ == "__main__":
    print("Alas, poor Yorrick...")

    client = ChatClient(openai_api_key)

    resp = client.generate_response("Tell me how to make chocolate chip cookies in 100 words or less")
    print(">>> ", resp)
    client.speak(resp)
    resp = client.generate_response("Those were awful")
    print(">>> ", resp)
    client.speak(resp)
    
