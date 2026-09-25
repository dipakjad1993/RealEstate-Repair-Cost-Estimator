# Contributing

## Provenance contract (non-negotiable)
Every number shown to a user carries one of 5 canonical badges:
`VERIFIED` · `USER_PROVIDED` · `MODELED` · `REQUIRES_KEY` · `UNAVAILABLE`.
Never present a deterministic estimate as a quote. Never invent firm names,
license numbers, permit histories, or comps. Honest `UNAVAILABLE` beats a guess.

## Language rules
- Say **deterministic estimate / market-baseline estimate**. Never "simulate".
- Official sources only: FEMA NFHL WMS/ArcGIS, USGS Design Maps + Earthquake
  Catalog, Census Geocoder + ACS, BLS OEWS/PPI, CPSC recalls, Open-Meteo.
  Third-party proxies (floodzonemap.org, faultlinemap.com, Nominatim) are
  **fallbacks** and must be labeled as such in provenance detail.

## Dev loop
```bash
python -m venv .venv && .venv/Scripts/activate  # or source .venv/bin/activate
pip install -r requirements.txt
ruff check . && ruff format --check .
pytest -q
streamlit run app.py
# API: uvicorn api_server:app --port 8000
```

## Adding a data source
1. Add fetcher in `engines/real_data_fetcher.py` using `shared_session()`
   (retries + backoff + timeout + latency recording).
2. Return `DataResult(value, Provenance(...))` with official URL.
3. Add health probe in `check_api_health(detailed=True)`.
4. Add a test in `tests/` asserting graceful `UNAVAILABLE` on network failure
   (no live calls in CI — mock `requests`).

## Config data
Canonical tables live versioned in `data/*.json` (`config_version` field).
`config.py` is a thin compat loader — do not add new hardcoded tables there.
