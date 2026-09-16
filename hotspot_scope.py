"""Scope handling for Chiang Mai hotspot sources.

GISTDA/data.go.th resources may be province-level aggregates without coordinates.
Those records are retained as a province-level indicator and are never assigned
to an individual park without spatial evidence.
"""

from __future__ import annotations

from typing import Iterable


CHIANG_MAI = "เชียงใหม่"


def normalize_province_hotspot(row: dict) -> dict | None:
    """Normalize a province-level hotspot row into the canonical scope.

    Returns None for records outside Chiang Mai. ``park_id`` deliberately stays
    None because an aggregate province count cannot identify a park.
    """

    province = str(row.get("province") or row.get("จังหวัด") or "").strip()
    if province and CHIANG_MAI not in province:
        return None
    count = row.get("hotspot_count", row.get("จำนวนจุดความร้อน", 0))
    try:
        count = int(str(count).replace(",", "").strip() or 0)
    except ValueError:
        count = 0
    return {
        "park_id": None,
        "geography_level": "province",
        "province": CHIANG_MAI,
        "record_date": row.get("record_date") or row.get("วันที่"),
        "hotspot_count": max(0, count),
        "source_name": row.get("source_name", "gistda_chiang_mai"),
    }


def filter_coordinate_hotspots(
    rows: Iterable[dict],
    *,
    west: float = 98.0,
    south: float = 17.2,
    east: float = 99.5,
    north: float = 20.5,
) -> list[dict]:
    """Apply a Chiang Mai bounding-box filter to coordinate-level records.

    This is intentionally a first-pass filter. Park-level assignment still
    requires park polygon geometry and is not inferred from a centroid.
    """

    filtered = []
    for row in rows:
        try:
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        if south <= latitude <= north and west <= longitude <= east:
            filtered.append(row)
    return filtered

