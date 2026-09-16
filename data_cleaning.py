"""Step 5: normalize, scope-filter, and combine the ingested datasets."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
PROCESSED_DIR = ROOT / "data" / "processed"
SOURCE_URL = "https://catalog.dnp.go.th/dataset/91d66c6a-5b88-41ee-8597-11be8aec5aa6/resource/be300299-f9a3-4eac-b558-0c088dd77a64/download/tourism59-68.csv"

PARK_IDS = {
    "ดอยอินทนนท์": "doi_inthanon",
    "ดอยสุเทพ-ปุย": "doi_suthep_pui",
    "ศรีลานนา": "sri_lanna",
    "แม่ตะไคร้": "mae_takhrai",
    "ออบหลวง": "ob_luang",
    "ดอยผ้าห่มปก": "doi_pha_hom_pok",
    "ผาแดง": "pha_daeng",
    "ขุนขาน": "khun_khan",
    "แม่วาง": "mae_wang",
    "ห้วยน้ำดัง": "huai_nam_dang",
    "แม่ปิง": "mae_ping",
}

MONTHS = {
    "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3,
    "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
    "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9,
}


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def normalize_park_name(value: str | None) -> str | None:
    """Map source name variants to the canonical scope, excluding proposed parks."""

    name = clean_text(value).replace("–", "-").replace("—", "-")
    if "เตรียมการ" in name:
        return None
    for canonical in PARK_IDS:
        if canonical in name:
            return canonical
    return None


def parse_number(value: str | None) -> int | float | None:
    text = clean_text(value).replace(",", "")
    if not text or text in {"-", "ไม่มีข้อมูล", "N/A"}:
        return None
    try:
        number = float(text)
        return int(number) if number.is_integer() else number
    except ValueError:
        return None


def read_csv_rows(path: Path):
    for encoding in ("utf-8-sig", "cp874", "tis-620"):
        try:
            with path.open(encoding=encoding, newline="") as stream:
                yield from csv.DictReader(stream)
            return
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"Unable to decode {path}")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def process_tourism(source: Path) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    seen: set[tuple] = set()
    source_rows = 0
    excluded_rows = 0
    duplicate_rows = 0
    for raw in read_csv_rows(source):
        source_rows += 1
        if "16" not in clean_text(raw.get("สังกัด")):
            excluded_rows += 1
            continue
        park_name = normalize_park_name(raw.get("อุทยานแห่งชาติ"))
        if not park_name:
            excluded_rows += 1
            continue
        fiscal_year = parse_number(raw.get("ปี"))
        if not isinstance(fiscal_year, int):
            excluded_rows += 1
            continue
        for raw_month, month in MONTHS.items():
            value = parse_number(raw.get(f" {raw_month} "))
            if value is None:
                value = parse_number(raw.get(raw_month))
            key = (PARK_IDS[park_name], fiscal_year, month, "dnp_tourism")
            if key in seen:
                duplicate_rows += 1
                continue
            seen.add(key)
            calendar_year = fiscal_year - (1 if month >= 10 else 0) - 543
            rows.append({
                "park_id": PARK_IDS[park_name],
                "park_name": park_name,
                "province": "เชียงใหม่",
                "fiscal_year": fiscal_year,
                "calendar_year": calendar_year,
                "month": month,
                "thai_visitors": None,
                "foreign_visitors": None,
                "total_visitors": value,
                "source_name": "dnp_tourism",
                "source_url": SOURCE_URL,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "schema_version": "1.0",
            })
    return rows, {
        "source_rows": source_rows,
        "excluded_source_rows": excluded_rows,
        "normalized_rows": len(rows),
        "duplicate_keys_removed": duplicate_rows,
    }


def process_weather(sources: list[Path]) -> tuple[list[dict], dict]:
    coordinates = json.loads((ROOT / "park_coordinates.json").read_text(encoding="utf-8"))["parks"]
    display_to_id = {name: park_id for name, park_id in PARK_IDS.items()}
    buckets: dict[tuple, dict[str, float]] = defaultdict(lambda: {
        "temperature": 0.0, "temperature_count": 0,
        "humidity": 0.0, "humidity_count": 0,
        "rainfall": 0.0, "rainfall_count": 0,
        "wind": 0.0, "wind_count": 0, "observations": 0,
    })
    source_rows = 0
    for source in sources:
        payload = json.loads(source.read_text(encoding="utf-8"))
        items = payload if isinstance(payload, list) else [payload]
        if len(items) != len(coordinates):
            raise RuntimeError(f"Weather location count mismatch in {source.name}")
        for item, park in zip(items, coordinates):
            hourly = item["hourly"]
            for index, timestamp in enumerate(hourly["time"]):
                date = datetime.fromisoformat(timestamp)
                bucket = buckets[(display_to_id[park["park_name"]], date.year, date.month)]
                for source_field, total_field, count_field in (
                    ("temperature_2m", "temperature", "temperature_count"),
                    ("relative_humidity_2m", "humidity", "humidity_count"),
                    ("precipitation", "rainfall", "rainfall_count"),
                    ("wind_speed_10m", "wind", "wind_count"),
                ):
                    value = hourly[source_field][index]
                    if value is not None:
                        bucket[total_field] += value
                        bucket[count_field] += 1
                bucket["observations"] += 1
                source_rows += 1
    rows = []
    retrieved_at = datetime.now(timezone.utc).isoformat()
    for (park_id, year, month), bucket in sorted(buckets.items()):
        rows.append({
            "park_id": park_id, "calendar_year": year, "month": month,
            "avg_temperature_2m_c": round(bucket["temperature"] / bucket["temperature_count"], 3) if bucket["temperature_count"] else None,
            "avg_relative_humidity_pct": round(bucket["humidity"] / bucket["humidity_count"], 3) if bucket["humidity_count"] else None,
            "total_precipitation_mm": round(bucket["rainfall"], 3) if bucket["rainfall_count"] else None,
            "avg_wind_speed_10m_kmh": round(bucket["wind"] / bucket["wind_count"], 3) if bucket["wind_count"] else None,
            "weather_observations": int(bucket["observations"]),
            "source_name": "open_meteo", "retrieved_at": retrieved_at, "schema_version": "1.0",
        })
    return rows, {"source_files": len(sources), "source_rows": source_rows, "normalized_rows": len(rows), "duplicate_keys_removed": 0}


def build_combined(tourism_rows: list[dict], weather_rows: list[dict]) -> list[dict]:
    monthly = {(row["park_id"], row["calendar_year"], row["month"]): row for row in weather_rows}
    combined = []
    for tourism in tourism_rows:
        key = (tourism["park_id"], tourism["calendar_year"], tourism["month"])
        weather = monthly.get(key, {})
        combined.append({
            **tourism,
            "avg_temperature_2m_c": weather.get("avg_temperature_2m_c"),
            "avg_relative_humidity_pct": weather.get("avg_relative_humidity_pct"),
            "total_precipitation_mm": weather.get("total_precipitation_mm"),
            "avg_wind_speed_10m_kmh": weather.get("avg_wind_speed_10m_kmh"),
            "weather_observations": weather.get("weather_observations", 0),
        })
    return combined


def run() -> None:
    tourism_rows, tourism_report = process_tourism(CACHE_DIR / "tourism59-68.csv")
    yearly_weather = sorted(path for path in CACHE_DIR.glob("weather_????.json") if path.stem[-4:].isdigit())
    weather_sources = yearly_weather or [CACHE_DIR / "weather_2016-01-01_2016-01-07.json"]
    weather_rows, weather_report = process_weather(weather_sources)
    write_csv(PROCESSED_DIR / "tourism.csv", list(tourism_rows[0]), tourism_rows)
    write_csv(PROCESSED_DIR / "weather_monthly.csv", list(weather_rows[0]), weather_rows)
    combined = build_combined(tourism_rows, weather_rows)
    write_csv(PROCESSED_DIR / "combined_monthly.csv", list(combined[0]), combined)
    report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "national_parks_in_chiang_mai",
        "tourism": tourism_report,
        "weather": weather_report,
        "combined_monthly_rows": len(combined),
        "quality_rules": {
            "negative_visitor_values": sum(1 for row in tourism_rows if isinstance(row["total_visitors"], (int, float)) and row["total_visitors"] < 0),
            "invalid_park_ids": sum(1 for row in tourism_rows if row["park_id"] not in PARK_IDS.values()),
            "missing_total_visitors": sum(1 for row in tourism_rows if row["total_visitors"] is None),
        },
    }
    (PROCESSED_DIR / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
