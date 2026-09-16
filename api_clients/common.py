"""Small dependency-free HTTP and cache helpers."""

from __future__ import annotations

import json
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = "ChiangMaiNationalParkDataApp/0.1"


def fetch_bytes(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    retries: int = 3,
    retry_delay: float = 1.0,
) -> bytes:
    """Fetch a URL with a timeout and retry handling."""

    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(url, headers=request_headers)
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if attempt + 1 < retries:
                time.sleep(retry_delay * (attempt + 1))

    raise RuntimeError(f"Unable to fetch {url}: {last_error}") from last_error


def fetch_json(url: str, **kwargs: Any) -> Any:
    """Fetch and decode a JSON response."""

    return json.loads(fetch_bytes(url, **kwargs).decode("utf-8"))


def write_cache(path: str | Path, content: bytes) -> Path:
    """Write a cache file atomically so interrupted downloads do not corrupt it."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(destination)
    return destination


def read_json_cache(path: str | Path) -> Any | None:
    """Read a JSON cache file, returning None when it does not exist."""

    cache_path = Path(path)
    if not cache_path.exists():
        return None
    return json.loads(cache_path.read_text(encoding="utf-8"))

