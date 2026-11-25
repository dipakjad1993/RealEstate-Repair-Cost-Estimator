# ScopeProof — v4.0.0

[![CI](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator/actions/workflows/ci.yml/badge.svg)](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.56-red)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

ScopeProof turns inspection PDFs, photos, voice notes and floorplans into
**deterministic, provenance-tagged repair cost estimates**. Same inputs → same
outputs. Every figure carries exactly one badge. No hallucinated numbers.

## Numbers first

| Measure | Value | Source |
|---|---|---|
| Test suite | **103 passed** | `pytest -q` (CI-equivalent) |
| Coverage gate | **87.8% ≥ 85%** | 16 critical modules, `ci.yml` |
| Lint / format | **clean** | `ruff check . && ruff format --check .` |
| OpenAPI | **10 routes, CI-synced** | `static/openapi.json` vs generated spec |
| Dependencies | **0 known CVEs** | `pip-audit --strict` on resolved pins |
| Engine modules | 40+ | `engines/` |
| ZIP cost markets | 83 | `data/zip_cost_modifiers.json` (v2026.09.25) |

## Provenance contract

| Badge | Meaning |
|---|---|
| **VERIFIED** | Official source answered (Census/BLS/FEMA/USGS/CPSC/FRED) or evidence-backed user MLS |
| **USER_PROVIDED** | User quotes/rows/uploads — authoritative, always wins |
| **MODELED** | Deterministic estimate from benchmarks — **not a quote** |
| **REQUIRES_KEY** | Enrichment available after you set a free API key |
| **UNAVAILABLE** | Source unreachable — reported honestly, never guessed |

Property-based tests (Hypothesis) machine-check the badge invariant over
random findings × states × ZIPs. Cost line items carry `badge`, `as_of`,
`source_url`, `geo_factor`, `geo_basis`, `geo_dataset`; the API returns these as
first-class response fields.

## What is actually wired

- **Cost engine**: BLS OEWS state wages + BLS PPI materials + published
  per-unit repair benchmarks; ZIP modifier (83 markets) or state COL index
  localizes the *material* benchmark. Labor is not double-localized when BLS
  state wages are present. User quotes bypass geo entirely.
- **Geo**: official USGS Design Maps ASCE 7-22 first; faultlinemap.com mirror
  is a **MODELED proxy**, never VERIFIED. FEMA/proxy fallbacks are labeled.
- **Live sources**: Census Geocoder, USGS Earthquake Catalog, CPSC recalls,
  BLS PPI, Open-Meteo, FRED (with key), Census ACS (with key). Shared HTTP
  session with retries, timeouts and latency metrics. Health probes are cached
  10 minutes and never run on the estimate path.
- **Citable artifacts**: `GET /e/{estimate_id}` returns the estimate plus a
  markdown twin, schema.org Dataset JSON-LD and a citation string. The
  Streamlit export row includes a `.md` citation twin.
- **Nightly ETL**: `scripts/refresh_snapshots.py` + `.github/workflows/data-refresh.yml`
  write content-hashed snapshots with source URL, badge, fetched_at and sha256
  into `data/snapshots/` (committed; `SNAPSHOT_DIR` can point at object storage).
- **API**: `/v1/estimate_repair` (Idempotency-Key), `/e/{id}`,
  `/v1/compliance/eu-ai-act`, `/api/health`, `/metrics` (auth), `/s/{token}`,
  `/llms.txt`. OWASP headers, timing-safe auth, hashed rate-limit keys,
  append-only hash-chained audit log. OpenAPI drift fails CI.
- **MCP**: stdio JSON-RPC with tools (`estimate_repair`, `get_provenance_legend`,
  `get_macro_context`, `get_snapshot_manifest`, `get_compliance_pack`) and
  resources (`repair://provenance/legend`, `repair://cost-tables/{zip}`,
  `scopeproof://macro/fred`, `scopeproof://snapshots/manifest`).
- **Compliance**: EU AI Act Art. 11/13/14 documentation pack endpoint;
  ECOA disparate-impact screen; all generated legal artifacts carry
  `ATTORNEY_REVIEW_REQUIRED: true`.

## Limitations (read this)

- This is **decision support, not a quote, inspection, appraisal or engineering
  opinion**. Actual bids vary; verify with licensed local professionals.
- Benchmarks are national published ranges; with only 83 ZIP markets, most ZIPs
  fall back to the state COL index (or 1.0 if the state is unknown).
- `citable_engine` produces artifacts and a prompt portfolio (200 prompts); it
  does **not** track live model mentions/citations. `llms.txt` is a courtesy
  file, not a traffic strategy.
- FRED, Census ACS and BLS full access need free API keys; without them the
  relevant figures are `REQUIRES_KEY`/`UNAVAILABLE`, never guessed.
- Live permit and comps providers have **no wired connectors**: with a key set
  they honestly return `PROVIDER_UNSUPPORTED`. Paste portal rows/comps instead.
- The PII vault is a **process-local, in-memory TTL dict** — not encrypted at
  rest and not shared across workers. `db_supabase` does **not** install RLS
  policies; the operator must apply and verify them. With no provider, a save
  returns an error status (no silent fake write).
- `/e/{estimate_id}` uses a 7-day in-process cache (durable persistence via
  Supabase/Postgres is operator-configured separately). `DATABASE_URL` reports
  a backend but has no insert path yet.
- Generated PDF/Excel/SEO content is deterministic; numbers are estimates.

## Quickstart

```bash
git clone https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator.git
cd RealEstate-Repair-Cost-Estimator
python -m venv .venv
# Windows: .venv\Scripts\activate  |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# REQUIRED for share links — generate and paste into .env:
python -c "import secrets; print(secrets.token_urlsafe(48))"   # SHARE_SECRET=...
streamlit run app.py                                           # :8501
```

Docker: `docker compose up --build` (Streamlit :8501 + FastAPI :8000 + Redis).

API / MCP:

```bash
export SHARE_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
export API_KEY=your-api-key
uvicorn api_server:app --port 8000
# POST /v1/estimate_repair  (Bearer auth + Idempotency-Key)
# GET  /e/{estimate_id} · /v1/compliance/eu-ai-act · /api/health · /metrics
printf '{"method":"tools/list","id":1}\n' | python mcp_server.py
```

Quality gates (identical to CI):

```bash
ruff check . && ruff format --check .
pytest -q
python -m pytest -q --cov=engines.audit_log --cov=engines.share_engine \
  --cov=engines.rate_limit --cov=engines.pii_vault --cov=engines.observability \
  --cov=engines.confidence_engine --cov=engines.citable_engine \
  --cov=engines.compliance_engine --cov=engines.etl_engine --cov=engines.fred_engine \
  --cov=engines.insurance_engine --cov=engines.investor_engine --cov=engines.legal_engine \
  --cov=engines.permit_live_engine --cov=engines.seo_engine --cov=engines.cost_engine \
  --cov-report=term-missing --cov-fail-under=85
```

## Project structure

```
app.py                    Streamlit entrypoint (intake, 5-badge UI, exports)
api_server.py             FastAPI v4.0 (estimates, canonical twin, compliance, health)
mcp_server.py             MCP tools + resources
config.py                 Versioned loader over data/*.json
data/                     Versioned datasets; snapshots/ committed with hash lineage
engines/                  40+ focused modules (cost, parser, provenance, ETL, ...)
scripts/refresh_snapshots.py  Nightly provenance-stamped ETL
static/                   Design system, PWA, llms.txt (courtesy), CI-synced openapi.json
tests/                    103 deterministic tests + Hypothesis invariants + golden eval
CHANGELOG.md              4.0.0 changes
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — provenance contract, "estimate, never
simulate" language, and how to add a data source. PR checklist:
[.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).

## Disclaimer

Informational purposes only — **not** engineering, legal, financial, or
insurance advice. Generated legal templates carry `ATTORNEY_REVIEW_REQUIRED:
true` and must be reviewed by a licensed attorney. Provided **as is**, without
warranty.

## License

MIT — see [LICENSE](LICENSE). · **Dipak Jad** · [@dipakjad1993](https://github.com/dipakjad1993)
