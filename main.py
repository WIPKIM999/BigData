"""FastAPI backend for the Chiang Mai national parks mini-project."""

from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = ROOT / "data" / "processed"

app = FastAPI(title="Chiang Mai National Parks Analytics API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])


def read_rows(filename: str) -> list[dict[str, str]]:
    path = PROCESSED_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"Processed data not found: {filename}")
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def as_number(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def filtered_rows(year: int | None, month: int | None, park: str | None) -> list[dict[str, str]]:
    rows = read_rows("combined_environment_monthly.csv")
    return [row for row in rows if
            (year is None or row.get("calendar_year") == str(year)) and
            (month is None or row.get("month") == str(month)) and
            (park is None or row.get("park_id") == park or row.get("park_name") == park)]


def ranged_rows(start_year: int | None = None, end_year: int | None = None, park: str | None = None) -> list[dict[str, str]]:
    rows = read_rows("combined_environment_monthly.csv")
    return [row for row in rows if
            (start_year is None or int(row["calendar_year"]) >= start_year) and
            (end_year is None or int(row["calendar_year"]) <= end_year) and
            (park is None or row.get("park_id") == park or row.get("park_name") == park)]


def park_catalog(rows: list[dict[str, str]] | None = None) -> dict[str, str]:
    return {row["park_id"]: row["park_name"] for row in (rows or read_rows("combined_environment_monthly.csv"))}


def validate_range(start_year: int, end_year: int) -> None:
    if start_year > end_year:
        raise HTTPException(status_code=422, detail="start_year must not exceed end_year")


def monthly_totals(rows: list[dict[str, str]]) -> list[dict[str, int]]:
    totals: dict[tuple[int, int], float] = defaultdict(float)
    for row in rows:
        totals[(int(row["calendar_year"]), int(row["month"]))] += as_number(row.get("total_visitors")) or 0
    return [{"calendar_year": year, "month": month, "total_visitors": int(value)} for (year, month), value in sorted(totals.items())]


@app.get("/")
def root() -> dict[str, str]:
    return {"name": app.title, "dashboard": "/dashboard", "docs": "/docs", "health": "/health"}


@app.get("/dashboard", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(ROOT / "dashboard.html")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "scope": "national_parks_in_chiang_mai", "data_available": (PROCESSED_DIR / "combined_environment_monthly.csv").exists()}


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    rows = read_rows("combined_environment_monthly.csv")
    years = sorted({int(row["calendar_year"]) for row in rows})
    parks = sorted(({"park_id": park_id, "park_name": name} for park_id, name in park_catalog(rows).items()), key=lambda item: item["park_name"])
    weather_rows = sum(1 for row in rows if as_number(row.get("avg_temperature_2m_c")) is not None)
    environment_rows = len({(row["calendar_year"], row["month"]) for row in rows if as_number(row.get("pm25_max_ug_m3")) is not None})
    return {
        "parks": parks, "years": years,
        "coverage": {
            "tourism_rows": len(rows), "weather_rows": weather_rows,
            "weather_percent": round(weather_rows / len(rows) * 100, 2) if rows else 0,
            "environment_months": environment_rows,
        },
        "notes": {
            "weather": "Reference point per park; not an area-wide average.",
            "environment": "PM2.5 and hotspot are Chiang Mai province-level indicators.",
        },
    }


@app.get("/api/analytics-report")
def analytics_report() -> dict[str, Any]:
    path = PROCESSED_DIR / "analytics_report.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="Analytics report is not available")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/summary")
def summary(year: int | None = Query(None), month: int | None = Query(None, ge=1, le=12), park: str | None = Query(None)) -> dict[str, Any]:
    rows = filtered_rows(year, month, park)
    totals: dict[str, float] = {}
    for row in rows:
        name = row.get("park_name", "unknown")
        totals[name] = totals.get(name, 0) + (as_number(row.get("total_visitors")) or 0)
    top = max(totals.items(), key=lambda item: item[1]) if totals else (None, 0)
    total = int(sum(totals.values()))
    previous_total = None
    yoy_percent = None
    if year is not None:
        previous_total = sum(as_number(row.get("total_visitors")) or 0 for row in filtered_rows(year - 1, month, park))
        if previous_total:
            yoy_percent = round((total - previous_total) / previous_total * 100, 2)
    return {"filters": {"year": year, "month": month, "park": park}, "total_visitors": total, "parks_with_data": len(totals), "top_park": top[0], "top_park_visitors": int(top[1]), "rows": len(rows), "previous_year_visitors": int(previous_total) if previous_total is not None else None, "yoy_percent": yoy_percent}


@app.get("/api/monthly-visitors")
def monthly_visitors(year: int | None = Query(None), park: str | None = Query(None)) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str], float] = {}
    for row in filtered_rows(year, None, park):
        key = (row.get("calendar_year", ""), row.get("month", ""))
        totals[key] = totals.get(key, 0) + (as_number(row.get("total_visitors")) or 0)
    return [{"calendar_year": int(y), "month": int(m), "total_visitors": int(v)} for (y, m), v in sorted(totals.items())]


@app.get("/api/trends")
def trends(
    metric: str = Query("visitors", pattern="^(visitors|pm25|max_pm25|hotspot|rainfall|temperature)$"),
    start_year: int = Query(2015), end_year: int = Query(2025), park: str | None = Query(None),
) -> list[dict[str, Any]]:
    validate_range(start_year, end_year)
    rows = ranged_rows(start_year, end_year, park)
    field_map = {"pm25": "pm25_max_ug_m3", "max_pm25": "pm25_max_ug_m3", "hotspot": "hotspot_count", "rainfall": "total_precipitation_mm", "temperature": "avg_temperature_2m_c"}
    if metric == "visitors":
        return monthly_totals(rows)
    field = field_map[metric]
    monthly: dict[tuple[int, int], list[float]] = defaultdict(list)
    for row in rows:
        value = as_number(row.get(field))
        if value is not None:
            monthly[(int(row["calendar_year"]), int(row["month"]))].append(value)
    result = []
    for (year, month), values in sorted(monthly.items()):
        value = values[0] if metric in {"pm25", "max_pm25", "hotspot"} else sum(values) / len(values)
        result.append({"calendar_year": year, "month": month, "metric": metric, "value": round(value, 3)})
    return result


@app.get("/api/seasonality")
def seasonality(park: str | None = Query(None), start_year: int = Query(2015), end_year: int = Query(2025)) -> list[dict[str, Any]]:
    validate_range(start_year, end_year)
    rows = ranged_rows(start_year, end_year, park)
    totals: dict[int, float] = defaultdict(float)
    years: dict[int, set[int]] = defaultdict(set)
    for row in rows:
        month, year = int(row["month"]), int(row["calendar_year"])
        totals[month] += as_number(row.get("total_visitors")) or 0
        years[month].add(year)
    return [{"month": month, "total_visitors": int(totals[month]), "average_visitors": round(totals[month] / len(years[month]), 2) if years[month] else 0} for month in range(1, 13)]


@app.get("/api/compare")
def compare(
    park_a: str = Query(...), park_b: str = Query(...),
    start_year: int = Query(2015), end_year: int = Query(2025),
) -> dict[str, Any]:
    validate_range(start_year, end_year)
    catalog = park_catalog()
    name_to_id = {name: park_id for park_id, name in catalog.items()}
    park_a = name_to_id.get(park_a, park_a)
    park_b = name_to_id.get(park_b, park_b)
    if park_a == park_b:
        raise HTTPException(status_code=422, detail="Choose two different parks")
    if park_a not in catalog or park_b not in catalog:
        raise HTTPException(status_code=404, detail="Park not found")

    weather_fields = {
        "temperature": "avg_temperature_2m_c", "humidity": "avg_relative_humidity_pct",
        "rainfall": "total_precipitation_mm", "wind": "avg_wind_speed_10m_kmh",
    }
    payload: dict[str, Any] = {}
    for key, park_id in (("park_a", park_a), ("park_b", park_b)):
        rows = ranged_rows(start_year, end_year, park_id)
        if not rows:
            raise HTTPException(status_code=404, detail=f"No data for {catalog[park_id]} in selected range")
        timeline = monthly_totals(rows)
        total = sum(item["total_visitors"] for item in timeline)
        peak = max(timeline, key=lambda item: item["total_visitors"])
        monthly = seasonality(park_id, start_year, end_year)
        weather = {}
        completeness = {}
        for metric, field in weather_fields.items():
            values = [value for row in rows if (value := as_number(row.get(field))) is not None]
            weather[metric] = round(sum(values) / len(values), 3) if values else None
            completeness[metric] = {"available": len(values), "expected": len(rows), "percent": round(len(values) / len(rows) * 100, 2) if rows else 0}
        payload[key] = {"park_id": park_id, "park_name": catalog[park_id], "total_visitors": total, "monthly_average": round(total / len(timeline), 2), "peak": peak, "timeline": timeline, "seasonality": monthly, "weather": weather, "completeness": completeness}

    a, b = payload["park_a"], payload["park_b"]
    winner, other = (a, b) if a["total_visitors"] >= b["total_visitors"] else (b, a)
    difference = winner["total_visitors"] - other["total_visitors"]
    difference_percent = round(difference / other["total_visitors"] * 100, 2) if other["total_visitors"] else None
    payload.update({
        "range": {"start_year": start_year, "end_year": end_year},
        "winner": winner["park_id"], "difference_visitors": difference, "difference_percent": difference_percent,
        "insights": [
            f"{winner['park_name']} มียอดนักท่องเที่ยวรวมสูงกว่า {other['park_name']} {difference:,} คน" + (f" หรือ {difference_percent}%" if difference_percent is not None else ""),
            f"เดือนสูงสุดของ {a['park_name']} คือ {a['peak']['month']}/{a['peak']['calendar_year']} และ {b['park_name']} คือ {b['peak']['month']}/{b['peak']['calendar_year']}",
            "ข้อมูลอากาศใช้จุดอ้างอิงของอุทยาน ส่วน PM2.5 และ hotspot เป็นตัวชี้วัดระดับจังหวัดและไม่ใช้ตัดสินผู้ชนะ",
        ],
    })
    return payload


@app.get("/api/park-visitors")
def park_visitors(year: int | None = Query(None), month: int | None = Query(None)) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str], float] = {}
    for row in filtered_rows(year, month, None):
        key = (row.get("park_id", ""), row.get("park_name", ""))
        totals[key] = totals.get(key, 0) + (as_number(row.get("total_visitors")) or 0)
    return sorted([{"park_id": p[0], "park_name": p[1], "total_visitors": int(v)} for p, v in totals.items()], key=lambda item: item["total_visitors"], reverse=True)


@app.get("/api/environment")
def environment(year: int | None = Query(None), month: int | None = Query(None, ge=1, le=12)) -> list[dict[str, Any]]:
    monthly: dict[tuple[str, str], dict[str, Any]] = {}
    fields = ("pm25_max_ug_m3", "pm25_exceed_days", "hotspot_count")
    for row in filtered_rows(year, month, None):
        key = (row.get("calendar_year", ""), row.get("month", ""))
        entry = monthly.setdefault(key, {"calendar_year": int(key[0]), "month": int(key[1])})
        for field in fields:
            value = as_number(row.get(field))
            if value is not None:
                entry[field] = value
    return [monthly[key] for key in sorted(monthly)]


@app.get("/api/data")
def data_explorer(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
    start_year: int = Query(2015), end_year: int = Query(2025), park: str | None = Query(None),
    sort_by: str = Query("calendar_year", pattern="^(calendar_year|month|park_name|total_visitors)$"),
    direction: str = Query("asc", pattern="^(asc|desc)$"),
) -> dict[str, Any]:
    validate_range(start_year, end_year)
    rows = ranged_rows(start_year, end_year, park)
    numeric = {"calendar_year", "month", "total_visitors"}
    rows.sort(key=lambda row: as_number(row.get(sort_by)) if sort_by in numeric else row.get(sort_by, ""), reverse=direction == "desc")
    start = (page - 1) * page_size
    return {"page": page, "page_size": page_size, "total": len(rows), "rows": rows[start:start + page_size]}


@app.get("/api/export.csv")
def export_csv(start_year: int = Query(2015), end_year: int = Query(2025), park: str | None = Query(None)) -> StreamingResponse:
    validate_range(start_year, end_year)
    rows = ranged_rows(start_year, end_year, park)
    if not rows:
        raise HTTPException(status_code=404, detail="No rows to export")
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return StreamingResponse(iter([stream.getvalue().encode("utf-8-sig")]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=chiang_mai_parks.csv"})


@app.post("/api/refresh")
def refresh() -> dict[str, Any]:
    try:
        subprocess.run([sys.executable, str(ROOT / "data_cleaning.py")], cwd=ROOT, check=True, capture_output=True, text=True)
        subprocess.run([sys.executable, str(ROOT / "analytics.py")], cwd=ROOT, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        return {"status": "fallback_cache", "message": "Refresh failed; last processed cache remains available.", "error": (error.stderr or str(error))[-500:]}
    return {"status": "refreshed", "message": "Processed datasets and analytics report rebuilt from local cache.", "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}
