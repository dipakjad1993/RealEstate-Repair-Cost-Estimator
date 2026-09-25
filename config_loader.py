"""Versioned config dataset loader (enterprise).

Canonical cost/config tables live in data/*.json with data/config_version.json.
This loader reads them once, caches in memory, and exposes dicts.
Override directory via CONFIG_DATA_DIR env var. Falls back to bundled JSON.
"""

import json
import os
from functools import lru_cache
from pathlib import Path

_BASE = Path(__file__).resolve().parent
DATA_DIR_CANDIDATE = os.environ.get("CONFIG_DATA_DIR", str(_BASE / "data"))


@lru_cache(maxsize=1)
def _manifest():
    d = Path(DATA_DIR_CANDIDATE)
    mf = d / "config_version.json"
    if mf.exists():
        return json.loads(mf.read_text(encoding="utf-8"))
    return {"version": "2026.09.25-embedded", "datasets": {}}


def config_version():
    return _manifest().get("version", "unknown")


@lru_cache(maxsize=32)
def load_dataset(name: str):
    d = Path(DATA_DIR_CANDIDATE)
    f = d / (name + ".json")
    if not f.exists():
        return None
    payload = json.loads(f.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload
