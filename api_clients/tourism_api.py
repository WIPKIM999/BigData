"""data.go.th/CKAN helper for discovering and downloading tourism resources."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from .common import fetch_bytes, fetch_json, write_cache


CATALOG_API = "https://data.go.th/api/3/action/package_show?id="
TOURISM_DATASET_ID = "gdpublish-stat-tourism"


def discover_resources(dataset_id: str = TOURISM_DATASET_ID) -> list[dict]:
    """Return resources exposed by the catalog for a dataset."""

    payload = fetch_json(f"{CATALOG_API}{quote(dataset_id)}")
    if not payload.get("success"):
        raise RuntimeError(f"Catalog returned an unsuccessful response: {payload}")
    return payload["result"].get("resources", [])


def download_resource(resource_url: str, cache_path: str | Path) -> Path:
    """Download a raw tourism resource without assuming its file format."""

    content = fetch_bytes(resource_url)
    return write_cache(cache_path, content)


def write_resource_manifest(resources: list[dict], path: str | Path) -> Path:
    """Save resource metadata for reproducibility and later source selection."""

    content = json.dumps(resources, ensure_ascii=False, indent=2).encode("utf-8")
    return write_cache(path, content)

