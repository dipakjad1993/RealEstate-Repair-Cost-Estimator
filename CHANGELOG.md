# Changelog

All notable changes to this project are documented here. Badges are authoritative:
VERIFIED (official source answered), USER_PROVIDED (authoritative user row),
MODELED (deterministic estimate), REQUIRES_KEY, UNAVAILABLE.

## 4.0.0 — 2026-11-25 (ScopeProof)

### Fixed
- Seismic hazard now queries the official USGS Design Maps ASCE 7-22 endpoint first;
  the faultlinemap.com mirror is labeled MODELED proxy, never VERIFIED.
- FEMA/USGS fallback proxies in `gov_sources_v2` no longer claim VERIFIED.
- `wwwiii.org` typo fixed to `www.iii.org` in the insurance dataset and engine.
- SEO markdown no longer claims "verified cost matrix"; cost figures are MODELED.
- Health probes are cached 10 minutes and removed from the per-estimate path.
- ZIP/state cost-of-living datasets are wired into `calculate_cost_bounds` with
  `geo_factor` / `geo_basis` / `geo_dataset` fields (no labor double counting).
- `pip-audit` is fail-closed; Trivy action pinned to v0.36.0; CVE-triaged deps
  (streamlit 1.56, requests 2.34, urllib3 2.8, fpdf2 2.8.8+, pytest 9.1).

### Added
- `GET /e/{estimate_id}` — citable estimate twin (markdown + JSON-LD + citation).
- `GET /v1/compliance/eu-ai-act` — EU AI Act Art. 11/13/14 documentation pack.
- FRED macro anchors and ETL snapshot manifest surfaced on `/api/health`.
- Citation-twin (.md) export button in the Streamlit app.
- Hashed rate-limit keys and auth on `/metrics`.
- `.dockerignore` and isolated pytest audit log.

### Removed
- `legacy/` quarantine (fully migrated); `config.legacy.py` and `utils/` remain deleted.
