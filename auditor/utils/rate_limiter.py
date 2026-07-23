"""
Retry logic with exponential backoff for AWS API rate limiting.

AWS throttles API calls under heavy usage (ThrottlingException,
RequestLimitExceeded). Since scanners will make many API calls per
region in Week 2, this decorator wraps any Boto3 call with automatic
retries and exponential backoff + jitter, rather than letting the
whole scan crash on a transient throttle.
"""

from __future__ import annotations

import random
import time
from functools import wraps
from typing import Callable, TypeVar

from botocore.exceptions import ClientError

T = TypeVar("T")

THROTTLE_ERROR_CODES = {
    "Throttling",
    "ThrottlingException",
    "RequestLimitExceeded",
    "TooManyRequestsException",
    "ProvisionedThroughputExceededException",
}


def with_retry(
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
):
    """
    Decorator: retries a function on AWS throttling errors using
    exponential backoff with jitter.

    Non-throttling errors (e.g. permission denied, invalid parameter)
    are re-raised immediately — retrying those would just waste time.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    attempt += 1

                    if error_code not in THROTTLE_ERROR_CODES:
                        raise

                    if attempt >= max_attempts:
                        raise

                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    delay += random.uniform(0, delay * 0.1)
                    time.sleep(delay)

        return wrapper

    return decorator