"""Dependency-free ingestion helpers for CSV/JSON source data."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


def iter_csv_rows(path: str | Path) -> Iterator[dict[str, str]]:
    """Yield CSV rows with a small encoding fallback for Thai source files."""

    source = Path(path)
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "cp874", "tis-620"):
        try:
            with source.open("r", encoding=encoding, newline="") as stream:
                yield from csv.DictReader(stream)
            return
        except UnicodeDecodeError as error:
            last_error = error
    raise RuntimeError(f"Unable to decode CSV {source}") from last_error


def csv_profile(path: str | Path) -> dict:
    """Return reproducible, lightweight profiling information for a CSV."""

    source = Path(path)
    row_count = 0
    columns: list[str] = []
    null_counts: dict[str, int] = {}
    for row in iter_csv_rows(source):
        if not columns:
            columns = list(row.keys())
            null_counts = {column: 0 for column in columns}
        row_count += 1
        for column, value in row.items():
            if value is None or not str(value).strip():
                null_counts[column] += 1
    return {
        "path": str(source),
        "row_count": row_count,
        "columns": columns,
        "null_counts": null_counts,
        "sha256": sha256_file(source),
    }


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_ingestion_metadata(
    path: str | Path,
    *,
    source_name: str,
    source_url: str,
    response_format: str,
    profile: dict,
    start_date: str | None = None,
    end_date: str | None = None,
    http_status: int = 200,
) -> Path:
    """Write a metadata sidecar next to an ingested file."""

    destination = Path(path)
    payload = {
        "source_name": source_name,
        "request_url": source_url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "start_date": start_date,
        "end_date": end_date,
        "http_status": http_status,
        "response_format": response_format,
        **profile,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination

