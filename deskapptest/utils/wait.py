import time
from typing import Callable, Optional as Opt, Tuple

from deskapptest.utils.conf import read_toml


class TimeoutMs:
    instant = read_toml("project-configuration.timeout-ms", "instant")
    short = read_toml("project-configuration.timeout-ms", "short")
    mid = read_toml("project-configuration.timeout-ms", "mid")
    long = read_toml("project-configuration.timeout-ms", "long")


def _init_wait(
    wait_ms: Opt[int],
    retry_ms: Opt[int],
    *,
    wait_ms_def: Opt[int] = None,
    retry_ms_def: Opt[int] = None,
) -> Tuple[int, int]:
    wait = wait_ms if wait_ms is not None else (wait_ms_def or TimeoutMs.mid)
    if retry_ms is not None and retry_ms < wait:
        retry = retry_ms
    else:
        retry = retry_ms_def or read_toml("project-configuration.retry-ms", "retry")
    return wait, retry


def pollwait(
    predicate_fn: Callable, *, wait_ms: Opt[int] = None, retry_ms: Opt[int] = None
):
    """
    :param int wait_ms: How long to wait for the predicate to be True. Accept 0 - means checking for a predicate only once without looping
    """
    wait, retry = _init_wait(wait_ms, retry_ms, wait_ms_def=TimeoutMs.long)
    waited = 0
    result = predicate_fn()
    while not result and wait > 0:
        time.sleep(retry / 1000)
        result = predicate_fn()
        waited += retry
        if waited >= wait:
            return None
    else:
        return result
