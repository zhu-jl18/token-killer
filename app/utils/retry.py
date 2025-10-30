"""Retry utilities using tenacity."""
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import aiohttp
from .logging import get_logger

logger = get_logger(__name__)


def create_retry_decorator(max_attempts: int = 3):
    """Create a retry decorator for HTTP calls."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            aiohttp.ClientError,
            aiohttp.ServerTimeoutError,
            TimeoutError,
        )),
        before_sleep=lambda retry_state: logger.warning(
            "retrying_request",
            attempt=retry_state.attempt_number,
            max_attempts=max_attempts,
        ),
    )
