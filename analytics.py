"""Step 6 analytics using only the Python standard library."""

from __future__ import annotations

import csv
import json
import math
import time
import tracemalloc
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = ROOT / "data" / "processed"
CACHE_DIR = ROOT / "cache"

THAI_MONTHS = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
    "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
    "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def number(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    x_mean, y_mean = mean(xs), mean(ys)
    x_delta = [x - x_mean for x in xs]
    y_delta = [y - y_mean for y in ys]
    denominator = math.sqrt(sum(value * value for value in x_delta) * sum(value * value for value in y_delta))
    return round(sum(x * y for x, y in zip(x_delta, y_delta)) / denominator, 4) if denominator else None


def summary_metrics(rows: list[dict[str, str]]) -> dict:
    values = [(row["park_name"], number(row.get("total_visitors")) or 0) for row in rows]
    totals = defaultdict(float)
    for park, value in values:
        totals[park] += value
    top_park = max(totals, key=totals.get) if totals else None
    return {
        "total_visitors": int(sum(value for _, value in values)),
        "parks_with_data": len(totals),
        "tourism_rows": len(rows),
        "top_park": top_park,
        "top_park_visitors": int(totals[top_park]) if top_park else 0,
    }


def monthly_trend(rows: list[dict[str, str]]) -> list[dict]:
    totals = defaultdict(float)
    for row in rows:
        key = (int(row["calendar_year"]), int(row["month"]))
        totals[key] += number(row.get("total_visitors")) or 0
    return [
        {"calendar_year": year, "month": month, "total_visitors": int(total)}
        for (year, month), total in sorted(totals.items())
    ]


def park_ranking(rows: list[dict[str, str]]) -> list[dict]:
    totals = defaultdict(float)
    for row in rows:
        totals[row["park_name"]] += number(row.get("total_visitors")) or 0
    return [
        {"rank": rank, "park_name": park, "total_visitors": int(total)}
        for rank, (park, total) in enumerate(sorted(totals.items(), key=lambda item: item[1], reverse=True), 1)
    ]


def season(month: int) -> str:
    if month in (3, 4, 5):
        return "ร้อน"
    if month in (6, 7, 8, 9, 10):
        return "ฝน"
    return "หนาว"


def seasonality(rows: list[dict[str, str]]) -> list[dict]:
    totals = defaultdict(float)
    for row in rows:
        totals[season(int(row["month"]))] += number(row.get("total_visitors")) or 0
    return [
        {"season": name, "total_visitors": int(total)}
        for name, total in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


def weather_relationship(rows: list[dict[str, str]]) -> dict:
    pairs: dict[str, tuple[list[float], list[float]]] = {
        "temperature": ([], []),
        "rainfall": ([], []),
        "humidity": ([], []),
    }
    for row in rows:
        visitor = number(row.get("total_visitors"))
        if visitor is None:
            continue
        for name, field in {
            "temperature": "avg_temperature_2m_c",
            "rainfall": "total_precipitation_mm",
            "humidity": "avg_relative_humidity_pct",
        }.items():
            value = number(row.get(field))
            if value is not None:
                pairs[name][0].append(value)
                pairs[name][1].append(visitor)
    return {
        name: {"sample_size": len(xs), "pearson_r": pearson(xs, ys)}
        for name, (xs, ys) in pairs.items()
    }


def load_environment() -> dict[tuple[int, int], dict[str, float]]:
    """Load monthly Chiang Mai PM2.5 and hotspot indicators."""

    result: dict[tuple[int, int], dict[str, float]] = defaultdict(dict)
    for path, field, output_field in [
        (CACHE_DIR / "pm25_max.csv", "PM2.5 (ug/m3)", "pm25_max_ug_m3"),
        (CACHE_DIR / "pm25_days.csv", "จำนวนวันที่เกิน", "pm25_exceed_days"),
        (CACHE_DIR / "hotspots_chiang_mai.csv", "จำนวน", "hotspot_count"),
    ]:
        for row in read_csv(path):
            year = number(row.get("ปี "))
            month = THAI_MONTHS.get((row.get("เดือน") or "").strip())
            value = number(row.get(field))
            if year is None or month is None or value is None:
                continue
            calendar_year = int(year) - 543
            result[(calendar_year, month)][output_field] = value
    return result


def join_environment(rows: list[dict[str, str]], environment: dict[tuple[int, int], dict[str, float]]) -> list[dict]:
    """Attach province-level environment indicators to each tourism row."""

    joined = []
    for row in rows:
        key = (int(row["calendar_year"]), int(row["month"]))
        joined.append({**row, **environment.get(key, {})})
    return joined


def environment_relationship(rows: list[dict[str, str]]) -> dict:
    # Environment sources are province-level. Aggregate tourism across parks
    # first so the same province indicator is not counted once per park.
    monthly = {}
    for row in rows:
        key = (int(row["calendar_year"]), int(row["month"]))
        entry = monthly.setdefault(key, {"total_visitors": 0.0})
        entry["total_visitors"] += number(row.get("total_visitors")) or 0
        for field in ("pm25_max_ug_m3", "pm25_exceed_days", "hotspot_count"):
            value = number(row.get(field))
            if value is not None:
                entry[field] = value

    fields = {
        "pm25_max": "pm25_max_ug_m3",
        "pm25_exceed_days": "pm25_exceed_days",
        "hotspot_count": "hotspot_count",
    }
    result = {}
    for name, field in fields.items():
        pairs = [
            (entry.get(field), entry.get("total_visitors"))
            for entry in monthly.values()
            if entry.get(field) is not None
        ]
        xs = [pair[0] for pair in pairs]
        ys = [pair[1] for pair in pairs]
        available = len(pairs)
        result[name] = {
            "status": "available" if available else "not_available",
            "sample_size": available,
            "pearson_r": pearson(xs, ys),
            "note": "ตัวแปรเป็นระดับจังหวัด ไม่ใช่ค่าของอุทยานรายแห่งโดยตรง",
        }
    result["aggregation"] = "ยอดนักท่องเที่ยวรวมทุกอุทยานต่อเดือน"
    return result


def run() -> dict:
    started = time.perf_counter()
    tracemalloc.start()
    rows = read_csv(PROCESSED_DIR / "combined_monthly.csv")
    environment = load_environment()
    joined_rows = join_environment(rows, environment)
    report = {
        "summary": summary_metrics(rows),
        "monthly_trend": monthly_trend(rows),
        "park_ranking": park_ranking(rows),
        "seasonality": seasonality(rows),
        "weather_relationship": weather_relationship(rows),
        "environment_relationship": environment_relationship(joined_rows),
        "input_file": "data/processed/combined_monthly.csv",
        "input_rows": len(rows),
        "environment_months": len(environment),
    }
    if joined_rows:
        fields = list(dict.fromkeys(field for row in joined_rows for field in row))
        with (PROCESSED_DIR / "combined_environment_monthly.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(joined_rows)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    report["benchmark"] = {
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "peak_memory_mb": round(peak / 1024 / 1024, 4),
    }
    output = PROCESSED_DIR / "analytics_report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    run()
