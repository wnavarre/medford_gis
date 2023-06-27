import time

LAST = time.perf_counter()

def log_time(msg):
    global LAST
    now = time.perf_counter()
    print(msg, "after", time.perf_counter() - LAST)
    LAST = now
    
class TimerLog:
    def __init__(self, msg):
        self._msg = msg
        self._start = time.perf_counter()
    def stop(self):
        elapsed = time.perf_counter() - self._start
        print("{}: {}".format(self._msg, elapsed))
