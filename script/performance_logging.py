import time

LAST = time.perf_counter()

def log_time(msg):
    global LAST
    now = time.perf_counter()
    print(msg, "after", time.perf_counter() - LAST)
    LAST = now
    
