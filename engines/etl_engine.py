"""ETL snapshot layer — versioned data snapshots with row-level lineage.

Live fetch + 24h cache is not an audit trail. Snapshots are: every nightly
(or on-demand) ETL run writes a content-hashed snapshot of each dataset to
data/snapshots/ with a manifest recording source URL, retrieval timestamp,
row count, and sha256. Engines read from the latest snapshot when available
(fast, offline-demoable, auditable) and fall back to live fetch.

Layout:
  data/snapshots/
    manifest.json                     — index of all snapshots
    {dataset}_{YYYYMMDD}.json         — snapshot payload
    {dataset}_{YYYYMMDD}.meta.json    — lineage (source, hash, rows, retrieved_at)

This is deliberately SQLite/JSON-first (no warehouse dependency). The
manifest schema is object-storage ready: point SNAPSHOT_DIR at an S3/GCS
mount and the same code works.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_DIR = Path(os.environ.get("SNAPSHOT_DIR", "data/snapshots"))
MANIFEST_PATH = SNAPSHOT_DIR / "manifest.json"


def _load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": 1, "snapshots": {}}


def _save_manifest(m: dict):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(m, indent=2, sort_keys=True), encoding="utf-8")


def write_snapshot(dataset: str, payload, source_url: str = "", extra_meta: dict | None = None) -> dict:
    """Write a content-hashed snapshot + lineage meta. Returns the lineage record."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    data_path = SNAPSHOT_DIR / f"{dataset}_{today}.json"
    meta_path = SNAPSHOT_DIR / f"{dataset}_{today}.meta.json"
    data_path.write_bytes(raw)
    rows = len(payload) if isinstance(payload, list | dict) else 1
    meta = {
        "dataset": dataset,
        "snapshot_date": today,
        "source_url": source_url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "row_count": rows,
        "content_sha256": sha,
        "byte_size": len(raw),
        **(extra_meta or {}),
    }
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    manifest = _load_manifest()
    manifest["snapshots"][dataset] = meta
    _save_manifest(manifest)
    return meta


def read_latest_snapshot(dataset: str):
    """Read the most recent snapshot for a dataset. Returns (payload, meta) or (None, None)."""
    manifest = _load_manifest()
    meta = manifest.get("snapshots", {}).get(dataset)
    if not meta:
        return None, None
    data_path = SNAPSHOT_DIR / f"{dataset}_{meta['snapshot_date']}.json"
    if not data_path.exists():
        return None, None
    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        return None, None
    # Integrity check — content hash must match lineage record.
    sha = hashlib.sha256(data_path.read_bytes()).hexdigest()
    if sha != meta.get("content_sha256"):
        return None, None
    return payload, meta


def snapshot_manifest() -> dict:
    """Public manifest for the health page / API."""
    m = _load_manifest()
    return {
        "snapshot_dir": str(SNAPSHOT_DIR),
        "datasets": m.get("snapshots", {}),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
