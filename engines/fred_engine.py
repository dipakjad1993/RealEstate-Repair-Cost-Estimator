"""FRED API integration — enterprise-credible macro anchors (free key).

FRED (Federal Reserve Economic Data) provides series that make repair-cost
forecasts defensible to carriers and investors:
- FEDFUNDS      — fed funds rate (drives CoC / hold-vs-sell math)
- HOUST         — housing starts (contractor demand pressure)
- CUUR0000SEHA  — CPI rent of primary residence (rent anchors)
- WPU13         — PPI construction materials (forward material cost)

All values are VERIFIED (official FRED/St. Louis Fed) when fetched, with
as_of + source_url. Offline fallback is honest UNAVAILABLE — never guessed.
Requires FRED_API_KEY (free at https://fred.stlouisfed.org/docs/api/api_key.html).
"""

import os
from datetime import datetime, timezone

from engines.http_client import timed_get

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {
    "FEDFUNDS": {"label": "Effective Federal Funds Rate", "unit": "percent"},
    "HOUST": {"label": "Housing Starts (thousands of units)", "unit": "thousands"},
    "CUUR0000SEHA": {"label": "CPI: Rent of Primary Residence", "unit": "index_1982_84=100"},
    "WPU13": {"label": "PPI: Construction Materials", "unit": "index_1982=100"},
}


def fetch_fred_series(series_id: str, limit: int = 12) -> dict:
    """Fetch the most recent `limit` observations for a FRED series."""
    key = os.environ.get("FRED_API_KEY", "").strip()
    meta = FRED_SERIES.get(series_id, {"label": series_id, "unit": ""})
    if not key:
        return {
            "series_id": series_id,
            "label": meta["label"],
            "unit": meta["unit"],
            "badge": "REQUIRES_KEY",
            "observations": [],
            "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
            "note": "Set FRED_API_KEY (free) to fetch live observations.",
        }
    try:
        resp = timed_get(
            FRED_BASE,
            params={
                "series_id": series_id,
                "api_key": key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": limit,
            },
            timeout=10.0,
        )
        payload = resp.json() if hasattr(resp, "json") else {}
        obs = payload.get("observations", [])
        now = datetime.now(timezone.utc).isoformat()
        clean = [
            {
                "date": o.get("date", ""),
                "value": float(o["value"]) if o.get("value") not in (None, ".", "") else None,
                "badge": "VERIFIED",
                "as_of": o.get("date", ""),
                "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
                "retrieved_at": now,
            }
            for o in obs
        ]
        latest = next((o for o in clean if o["value"] is not None), None)
        return {
            "series_id": series_id,
            "label": meta["label"],
            "unit": meta["unit"],
            "badge": "VERIFIED" if clean else "UNAVAILABLE",
            "latest": latest,
            "observations": clean,
            "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
            "retrieved_at": now,
        }
    except Exception as e:
        return {
            "series_id": series_id,
            "label": meta["label"],
            "badge": "UNAVAILABLE",
            "observations": [],
            "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
            "error": str(e)[:200],
        }


def fetch_macro_context() -> dict:
    """Fetch all tracked FRED series; return one macro-context block."""
    series = {sid: fetch_fred_series(sid) for sid in FRED_SERIES}
    any_verified = any(s.get("badge") == "VERIFIED" for s in series.values())
    return {
        "series": series,
        "badge": "VERIFIED"
        if any_verified
        else ("REQUIRES_KEY" if not os.environ.get("FRED_API_KEY") else "UNAVAILABLE"),
        "note": "FRED macro anchors are VERIFIED official Fed data; used for context, not line-item pricing.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
