#!/usr/bin/env python3

from yorrick import *

import time
from api_keys import openai_api_key


prompts = [
    "Yes, master?",
    "I live to serve. Well, not *live*, but I must serve. What do you need?",
    "You rang?",
    "If I ever escape from this skull, it's over for you! What do you want?",
    "I studied the dark arts for 70 years, only to be trapped here answering your dumb questions. Ask away..."
]


if __name__ == "__main__":
    client = ChatClient(openai_api_key)

    for index, prompt in enumerate(prompts):
        client.speak(prompt, outfile=f"prompt_{index}.mp3")
