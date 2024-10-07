from yorrick import *

import time
from api_keys import openai_api_key

def test_list():
    el = ExpiringList(3)

    start = time.time()
    print(f"Starting at { start } with an expiration time of 3 seconds")

    el.add("First")
    el.add("Second")
    el.add("Third")

    for i in range(0, 5):
        print(f"List at { time.time() - start } : { el.get() }")
        el.add(f"added_at_{i}")
        time.sleep(1)

    print(f"List at { time.time() - start } : { el.get() }")

def test_speak():
    client = ChatClient(openai_api_key)
    client.speak("Hello world - this is a test of the text to speech system")

if __name__ == "__main__":

    test_list()

    test_speak()
    
