"""Polite HTTP client: descriptive UA, timeouts, retries with backoff, per-host min interval."""

import threading
import time
from urllib.parse import urlsplit

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

RETRY_STATUS = {429, 500, 502, 503, 504}


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRY_STATUS
    return isinstance(exc, httpx.TransportError)


class PoliteClient:
    def __init__(self, user_agent: str, timeout: float = 20.0, min_interval_s: float = 0.25):
        self._client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            timeout=timeout,
            follow_redirects=True,
        )
        self._min_interval = min_interval_s
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def _throttle(self, host: str) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self._last.get(host, 0.0) + self._min_interval - now
            self._last[host] = max(now, now + wait)
        if wait > 0:
            time.sleep(wait)

    @retry(
        retry=retry_if_exception(_retryable),
        stop=stop_after_attempt(4),
        wait=wait_exponential_jitter(initial=1, max=20),
        reraise=True,
    )
    def get_json(self, url: str, params: dict | None = None):
        self._throttle(urlsplit(url).netloc)
        r = self._client.get(url, params=params)
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
