# src/retry_helper.py
import time, functools
def retry(max_attempts=4, initial_delay=1.0, backoff=2.0, allowed_exceptions=(Exception,)):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_attempts+1):
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    if attempt == max_attempts:
                        raise
                    time.sleep(delay)
                    delay *= backoff
        return wrapper
    return deco
