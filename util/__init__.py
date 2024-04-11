import time
from typing import Callable


class TimeoutMs:
    instant = 1500
    short = 5000
    mid = 30000
    long = 60000


def pollwait(predicate: Callable, *, wait_ms=None, retry_ms=None):
    wait = wait_ms if wait_ms is not None else TimeoutMs.long
    retry = int(retry_ms if retry_ms is not None and retry_ms < wait else wait / 15)

    waited = 0
    result = predicate()
    while not result and wait > 0:
        time.sleep(retry / 1000)
        result = predicate()
        waited += retry
        if waited >= wait:
            return None
    else:
        return result
