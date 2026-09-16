"""Open-Meteo Historical Weather API client."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode

from .common import fetch_bytes, write_cache


BASE_URL = "https://archive-api.open-meteo.com/v1/archive"


def build_url(
    latitude: float | list[float],
    longitude: float | list[float],
    start_date: str,
    end_date: str,
    *,
    hourly: tuple[str, ...] = (
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
        "weather_code",
    ),
    timezone: str = "Asia/Bangkok",
) -> str:
    """Build a historical API URL for one or multiple park coordinates."""

    def coordinate(value: float | list[float]) -> str:
        if isinstance(value, list):
            return ",".join(str(item) for item in value)
        return str(value)

    query = urlencode(
        {
            "latitude": coordinate(latitude),
            "longitude": coordinate(longitude),
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(hourly),
            "timezone": timezone,
        }
    )
    return f"{BASE_URL}?{query}"


def fetch_weather(
    latitude: float | list[float],
    longitude: float | list[float],
    start_date: str,
    end_date: str,
    cache_path: str | Path,
) -> dict:
    """Fetch weather JSON and save the raw response to cache."""

    url = build_url(latitude, longitude, start_date, end_date)
    content = fetch_bytes(url, headers={"Accept": "application/json"})
    write_cache(cache_path, content)
    return json.loads(content.decode("utf-8"))

