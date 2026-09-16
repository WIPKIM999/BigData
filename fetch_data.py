"""Step 2/4 data-source smoke tests and raw-data ingestion commands.

Examples:
  python fetch_data.py sources
  python fetch_data.py weather --start 2016-01-01 --end 2016-01-07
  python fetch_data.py tourism
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from api_clients.tourism_api import discover_resources, download_resource, write_resource_manifest
from api_clients.weather_api import fetch_weather
from ingestion import csv_profile, write_ingestion_metadata


ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"

# Replace these centroids with verified coordinates before the full historical run.
PARK_TEST_COORDINATES = {
    "doi_inthanon": (18.588, 98.487),
    "doi_suthep_pui": (18.805, 98.921),
    "sri_lanna": (19.120, 99.050),
    "mae_takhrai": (18.800, 99.250),
    "ob_luang": (18.270, 98.440),
    "doi_pha_hom_pok": (19.960, 99.150),
    "pha_daeng": (19.500, 98.950),
    "khun_khan": (18.900, 98.700),
    "mae_wang": (18.550, 98.700),
    "huai_nam_dang": (19.310, 98.580),
    "mae_ping": (17.800, 98.850)
}


def command_sources(_: argparse.Namespace) -> None:
    resources = discover_resources()
    manifest = write_resource_manifest(resources, CACHE_DIR / "tourism_resources.json")
    print(f"Discovered {len(resources)} tourism resources")
    print(f"Manifest: {manifest}")
    for resource in resources:
        print(f"- {resource.get('format', '?')}: {resource.get('name', '?')} -> {resource.get('url', '?')}")


def command_weather(args: argparse.Namespace) -> None:
    latitudes = [value[0] for value in PARK_TEST_COORDINATES.values()]
    longitudes = [value[1] for value in PARK_TEST_COORDINATES.values()]
    result = fetch_weather(
        latitudes,
        longitudes,
        args.start,
        args.end,
        CACHE_DIR / f"weather_{args.start}_{args.end}.json",
    )
    cache_path = CACHE_DIR / f"weather_{args.start}_{args.end}.json"
    cache_path.with_suffix(".metadata.json").write_text(
        json.dumps({
            "source_name": "open_meteo",
            "request_url": "https://archive-api.open-meteo.com/v1/archive",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "start_date": args.start,
            "end_date": args.end,
            "locations": len(PARK_TEST_COORDINATES),
            "hourly_rows": sum(len(item["hourly"]["time"]) for item in result),
            "response_format": "json"
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"locations": len(PARK_TEST_COORDINATES), "result_type": type(result).__name__}, ensure_ascii=False))


def command_tourism(_: argparse.Namespace) -> None:
    resources = discover_resources()
    manifest = write_resource_manifest(resources, CACHE_DIR / "tourism_resources.json")
    print(f"Tourism resource manifest written to {manifest}")
    print("Select the CSV/XLSX resource after inspecting the manifest; do not assume a resource URL is permanent.")


def command_tourism_download(args: argparse.Namespace) -> None:
    resources = discover_resources()
    matches = [
        item for item in resources
        if item.get("format", "").upper() == "CSV"
        and args.year in item.get("name", "")
    ]
    if not matches:
        raise RuntimeError(f"No CSV tourism resource found for year {args.year}")
    resource = matches[0]
    output = ROOT / "data" / "raw" / f"tourism_{args.year}.csv"
    download_resource(resource["url"], output)
    profile = csv_profile(output)
    metadata_path = write_ingestion_metadata(
        output.with_suffix(".metadata.json"),
        source_name="dnp_tourism",
        source_url=resource["url"],
        response_format="csv",
        profile=profile,
    )
    print(json.dumps({"file": str(output), "metadata": str(metadata_path), "row_count": profile["row_count"]}, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sources = subparsers.add_parser("sources", help="discover data.go.th resources")
    sources.set_defaults(function=command_sources)

    tourism = subparsers.add_parser("tourism", help="discover tourism resources")
    tourism.set_defaults(function=command_tourism)

    tourism_download = subparsers.add_parser("tourism-download", help="download one yearly tourism CSV")
    tourism_download.add_argument("--year", default="2564", help="fiscal year in Buddhist Era, for example 2564")
    tourism_download.set_defaults(function=command_tourism_download)

    weather = subparsers.add_parser("weather", help="download a small weather smoke test")
    weather.add_argument("--start", default="2016-01-01")
    weather.add_argument("--end", default="2016-01-07")
    weather.set_defaults(function=command_weather)

    return parser


if __name__ == "__main__":
    arguments = build_parser().parse_args()
    arguments.function(arguments)
