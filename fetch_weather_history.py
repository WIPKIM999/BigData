"""Download Open-Meteo historical weather in resumable yearly cache files.

Examples:
  python3 fetch_weather_history.py
  python3 fetch_weather_history.py --start-year 2020 --end-year 2025
  python3 fetch_weather_history.py --year 2019 --force
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from api_clients.weather_api import fetch_weather


ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
PARKS = json.loads((ROOT / "park_coordinates.json").read_text(encoding="utf-8"))["parks"]


def valid_cache(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    items = payload if isinstance(payload, list) else [payload]
    return len(items) == len(PARKS) and all(item.get("hourly", {}).get("time") for item in items)


def fetch_year(year: int, *, force: bool = False) -> dict:
    destination = CACHE_DIR / f"weather_{year}.json"
    metadata = CACHE_DIR / f"weather_{year}.metadata.json"
    if destination.exists() and valid_cache(destination) and not force:
        payload = json.loads(destination.read_text(encoding="utf-8"))
        items = payload if isinstance(payload, list) else [payload]
        return {"year": year, "status": "cache", "hourly_rows": sum(len(item["hourly"]["time"]) for item in items)}

    result = fetch_weather(
        [park["latitude"] for park in PARKS],
        [park["longitude"] for park in PARKS],
        f"{year}-01-01",
        f"{year}-12-31",
        destination,
    )
    items = result if isinstance(result, list) else [result]
    if len(items) != len(PARKS) or not all(item.get("hourly", {}).get("time") for item in items):
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Malformed Open-Meteo response for {year}")
    hourly_rows = sum(len(item["hourly"]["time"]) for item in items)
    metadata.write_text(json.dumps({
        "source_name": "open_meteo",
        "year": year,
        "locations": len(PARKS),
        "hourly_rows": hourly_rows,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "coordinate_note": "reference point per park; not an area-wide average",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"year": year, "status": "downloaded", "hourly_rows": hourly_rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--year", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between new downloads to reduce rate limiting")
    args = parser.parse_args()
    years = [args.year] if args.year else list(range(args.start_year, args.end_year + 1))
    if any(year < 1940 or year > datetime.now().year for year in years):
        raise SystemExit("Year is outside Open-Meteo historical range")
    results = []
    failures = []
    for index, year in enumerate(years):
        try:
            result = fetch_year(year, force=args.force)
            results.append(result)
            print(json.dumps(result, ensure_ascii=False))
            if result["status"] == "downloaded" and index + 1 < len(years):
                time.sleep(max(args.delay, 0))
        except RuntimeError as error:
            failures.append({"year": year, "error": str(error)})
            print(json.dumps({"year": year, "status": "failed", "error": str(error)}, ensure_ascii=False))
    print(json.dumps({"years": len(results), "hourly_rows": sum(item["hourly_rows"] for item in results), "failures": [item["year"] for item in failures]}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
