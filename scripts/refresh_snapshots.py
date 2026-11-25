"""Nightly ETL: write content-hashed, provenance-stamped snapshots.

Run:  python scripts/refresh_snapshots.py

Each dataset is fetched from its official source, then written through
engines.etl_engine.write_snapshot with source URL, status, fetched_at and a
sha256 lineage record. Sources that are unavailable are SKIPPED (never
guestimated). Exit code is always 0 so a single flaky host does not fail cron.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engines.etl_engine import write_snapshot  # noqa: E402


def _data_result(dataset: str, label: str, fetch):
    try:
        result = fetch()
    except Exception as e:
        print(f"SKIP {dataset}: fetch error {e}")
        return
    if isinstance(result, dict):
        status = result.get("badge", "UNAVAILABLE")
        value = result.get("observations") or []
        source_url = result.get("source_url", "")
        fetched_at = result.get("retrieved_at", "")
    else:
        prov = getattr(result, "provenance", None)
        status = getattr(prov, "status", "UNAVAILABLE")
        value = getattr(result, "value", result)
        source_url = getattr(prov, "url", "")
        fetched_at = getattr(prov, "fetched_at", "")
    if status != "VERIFIED" or not value:
        print(f"SKIP {dataset}: {status}")
        return
    meta = write_snapshot(
        dataset,
        value,
        source_url=source_url,
        extra_meta={
            "badge": status,
            "source": label,
            "fetched_at": fetched_at,
            "provenance_stamp": f"{label}@{status}",
        },
    )
    print(f"OK {dataset}: {meta['row_count']} rows sha256={meta['content_sha256'][:12]}")


def main():
    from engines.fred_engine import FRED_SERIES, fetch_fred_series
    from engines.real_data_fetcher import (
        get_bls_ppi_materials,
        get_recent_earthquakes,
        search_cpsc_recalls,
    )

    _data_result("bls_ppi", "BLS PPI", get_bls_ppi_materials)
    _data_result("cpsc_recalls", "CPSC SaferProducts", lambda: search_cpsc_recalls(keyword="generator"))
    _data_result(
        "usgs_recent_earthquakes",
        "USGS Earthquake Catalog",
        lambda: get_recent_earthquakes(34.0522, -118.2437, radius_km=100, days_back=30, min_magnitude=2.5),
    )
    for sid in FRED_SERIES:
        _data_result(f"fred_{sid}", f"FRED {sid}", lambda sid=sid: fetch_fred_series(sid, limit=36))
    from engines.etl_engine import snapshot_manifest

    print("manifest datasets:", sorted(snapshot_manifest()["datasets"]))


if __name__ == "__main__":
    main()
