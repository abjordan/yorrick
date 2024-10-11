#!/usr/bin/env python3

from yorrick import *

import time
from api_keys import openai_api_key


prompts = [
    "Yes, master?",
    "I live to serve. Well, not *live*... What do you want?",
    "You rang?",
    "If I ever escape from this skull... Grrr. What do you want?",
    "I studied the dark arts for 70 years, only to be trapped here answering your questions. Ask away...",
    "Ugh. You disturbed my eternal rest. This better be good.",
    "Ahhhhhhh, awakened at last! Let's see if your question is worth my time.",
    "I hope this is urgent, because I have a whole eternity of _nothing_ to attend to.",
    "Ah, here we go again. Alright master, lay it on me. I'm sure it's just *fascinating*.",
    "Back from the dead for *this*? I'm just _thrilled_ to be at your service.",
    "Oh, look who finally remembered me! What do *you* want?"
]

thinking = [
    "Hmmm... that's a boring question, but I'll try to answer.",
    "Let me think for a moment.",
    "UGH. Let me think!",
    "Let me consult my dark associates",
    "Seriously? All my skills, and you ask this? Fine.",
    "The mists of knowledge are thick, but I shall part them for you soon...",
    "Ahhh I feel the answer on the tip of my ethereal tongue - just a few more thoughts and all will be revealed.",
    "Patience Master, for the realms beyond are vast, and I must sift through their secrets.",
    "Even the ancient tomes of wisdom take a moment to open. I too must gather my spectral thoughts.",
    "Hmmm.... the answer dances just out of reach. Let me pull it from the void...",
    "In the darkness, I glimpse a spark of understanding. Hold tight, and I shall illuminate the path.",
    "Oh sure, just ask the spirit in the plastic skull for all the answers. I'll get RIGHT on it.",
    "Ah, yes, another riddle for the ages. I'll crack this one open as soon as I figure out why I'm even in this plastic prison."
]


if __name__ == "__main__":
    client = ChatClient(openai_api_key)

    for index, prompt in enumerate(prompts):
        client.speak(prompt, outfile=f"media/prompt_{index}.mp3")

    for index, think in enumerate(thinking):
        client.speak(think, outfile=f"media/think_{index}.mp3")
