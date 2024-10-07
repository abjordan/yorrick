from yorrick import ExpiringList

import time

if __name__ == "__main__":

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
    
