# Real Estate Repair Cost Estimator — v3.4 Enterprise

[![CI](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator/actions/workflows/ci.yml/badge.svg)](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.37-red)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> **Provenance-tracked property intelligence.** Inspection PDFs, photos, voice walkthroughs, and floorplans become transparent, deterministic repair estimates across **21+ analysis modules** — powered by live government data, with every figure badged. **Nothing is fabricated. Estimates, never simulations.**

## Why this exists (2026)

> "Rebuilding cost models need to be very transparent and deterministic. The current LLMs and AIs don't meet that criteria... They can't be trusted because of hallucination."
> — Matt Wielbut, CTO, Openly (*Digital Insurance*, Oct 13 2026)

This tool is a direct answer to that. A deterministic, auditable, provenance-first estimate engine — the anti-black-box machine for an industry where 90% of firms are piloting AI and ~1% report transformative impact (Deloitte 2026). Same inputs → same outputs. Every number carries exactly one badge.

## The provenance contract

Every number carries exactly one badge:

| Badge | Meaning |
|---|---|
| 🟢 **VERIFIED** | Live government data (Census · BLS · FEMA · USGS · CPSC · FRED) or evidence-backed user MLS |
| 🟡 **USER_PROVIDED** | Your quotes, MLS rows, uploads — authoritative, always wins |
| 🔵 **MODELED** | Deterministic estimate from verified baselines — **not a quote** |
| 🟠 **REQUIRES_KEY** | Live enrichment available once an API key is configured |
| ⚪ **UNAVAILABLE** | Source unreachable — reported honestly, never guessed |

v3.4 enforces this contract inside the code: the investor engine's every heuristic is registered in `INVESTOR_HEURISTICS` and badged; insurance red-flag values carry `badge` + `source_url` + `as_of`; the cost engine stamps `badge`/`as_of`/`source_url` on every line item; the API returns per-figure provenance as first-class response fields. Property-based tests (Hypothesis) machine-check the invariant across random inputs.

## What v3.4 changed (enterprise transformation)

### Security (TIER 0)
- **Killed the dev HMAC default.** `SHARE_SECRET` is required; boot fails if unset or equal to the retired `dev-share-secret-change-me`. Rotation via `SHARE_SECRET_PREVIOUS`. See [SECURITY.md](SECURITY.md).
- **Timing-safe auth.** API-key checks use `hmac.compare_digest` (was plain `==`, a timing oracle).
- **OWASP headers** on every API response: CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, X-Request-ID.
- **Distributed rate limiting.** Redis-backed sliding window when `REDIS_URL` is set; in-memory fallback otherwise. Multi-replica ready.
- **Append-only audit log** (`engines/audit_log.py`): every estimate, share-token read, PII vault access, and failed auth — hash-chained, tamper-detectable, PII-redacted. Your SOC2 seed and carrier sales weapon.
- **PII vault** now audit-logs every store/get, purges on TTL and capacity, and the stray CJK character is gone.
- **Supply-chain CI:** Dependabot + pip-audit + Trivy on every PR. OpenAPI generated from FastAPI in CI and diffed against `static/openapi.json` — drift fails the build.

### Provenance contract fixes (TIER 1)
- **Investor engine**: every hardcoded heuristic (expense ratio, profit target, closing costs, CapEx reserve, ARV rehab multipliers, holding-cost rates, interest default, failure-probability curve, condition multipliers) is now registered in `INVESTOR_HEURISTICS` with badge + description + source note. `figure_provenance` and `heuristics_registry` ship in every response. User overrides flip badges to `USER_PROVIDED`.
- **Insurance red flags**: every rule now carries `badge: MODELED` + `source_url` (EPA/CPSC/NFPA/III/InterNACHI) + `as_of`. Fixed the regex-vs-substring bug — the previous substring matcher silently skipped every regex-style pattern (e.g. `roof.*1[3-9].years`); patterns are now applied as real case-insensitive regex with alternation.
- **Per-figure provenance in the API**: `/v1/estimate_repair` returns `line_items[]` each with `badge`, `as_of`, `source_url`, `retrieved_at` — first-class response fields, not buried in a badge. This is what makes you citable.
- **Hardcoded confidence killed.** The flat `0.85`/`0.75` priors in `parser_engine`/`voice_engine` are replaced by `engines/confidence_engine.py`: a deterministic, signal-weighted scorer (numeric measurements, component specificity, imperative verbs, location, hedging, source type) with a `calibrate()` path for fitting weights to a labeled corpus. `calibration_status: DEFAULT_WEIGHTS` until corpus-fitted — honest about what it is.

### Data layer (TIER 2)
- **FRED integration** (`engines/fred_engine.py`): fed funds, housing starts, CPI rent, PPI construction materials — VERIFIED official Fed data with `as_of` + `source_url`. Free key.
- **ETL snapshot pipeline** (`engines/etl_engine.py`): content-hashed, lineage-tracked snapshots under `data/snapshots/` with a manifest. Cache ≠ snapshot; snapshots give auditability, speed, and offline demos. Object-storage-ready (point `SNAPSHOT_DIR` at S3/GCS).

### API productization (TIER 4)
- **`/v1/estimate_repair`** with `Idempotency-Key` support (agents retry — you need this), richer provenance envelope, and structured logging. Legacy `/api/estimate_repair` preserved.
- **`/metrics`** Prometheus exposition: estimate volume, badge mix, **VERIFIED% North Star**, p95 latencies per host/engine.
- **Share portal XSS fixed**: all dynamic HTML is escaped (the previous lender portal interpolated room values raw into `<td>`).
- **MCP server** now exposes **resources** (`repair://provenance/legend`, `repair://cost-tables/{zip}`) alongside tools — agents cite resources; tools are for actions. Fixed the `rate_rooms` call that omitted `cost_by_finding` (produced zero-cost room rows over MCP).

### Observability (TIER 5)
- **Structured JSON logs** with `estimate_id`, badge counts, latencies — one JSON object per line, logfmt-compatible.
- **Badge-mix metrics**: `observe_badges()` tracks the North-Star VERIFIED% per estimate; rolling aggregates on the health page and `/metrics`. If VERIFIED% drops, the product is lying — now you'll see it.
- **OpenTelemetry hooks** (`trace_span`): no-op unless `OTEL_EXPORTER_OTLP_ENDPOINT` is set — the deterministic core never depends on it.

### Tests (TIER 6)
- **Property-based badge invariant** (Hypothesis): for random findings × states × ZIPs, every output figure carries exactly one valid badge, no nulls. Machine-checked.
- **Security tests**: dev-secret rejection, tamper detection, timing-safe auth, OWASP headers, HTML escaping.
- **MCP contract tests**: JSON-RPC frames for `tools/list`, `resources/list`, `resources/read`.
- **Coverage gate ≥85%** on the 16 critical security/provenance modules, enforced in CI.
- **Insurance regex tests** prove the previously-dead patterns now fire.
- **Investor provenance tests** prove every heuristic is badged.

### GEO / answer-surface strategy (TIER 7)
- **Citable answer artifacts** (`engines/citable_engine.py`): every export ships a markdown twin (answer capsule + number table with per-row badge + as_of + source + Q&A block + canonical URL) and schema.org Dataset JSON-LD. The PDF closes the deal; the markdown gets cited; the badge survives the citation. Attribution-proofing for the chat-window era.
- **Prompt portfolio** (`seo_engine.build_prompt_portfolio`): 200 ICP prompts × geos, with per-engine (ChatGPT/Gemini/Perplexity/AI Mode) mention-vs-citation tracking under the St. Gallen protocol (7+ runs/day, 2–4 week rolling windows). Citations ≠ mentions — track both.
- **Q&A blocks** on every programmatic page — the answer-shaped format AI engines actually cite.
- **llms.txt demoted to courtesy file** (honestly documented): 2026 data says it receives negligible direct LLM traffic. Kept for crawler politeness, removed as a strategy claim.

### Legal / compliance (TIER 8)
- **`ATTORNEY_REVIEW_REQUIRED: true`** hard-coded, non-removable, on every generated legal artifact (repair addenda, escrow holdbacks). Stamped into the payload and the document text.
- **EU AI Act documentation pack** (`engines/compliance_engine.eu_ai_act_documentation`): intended purpose, human-oversight path, training-data provenance (deterministic — none, the strongest answer), post-market monitoring.
- **ECOA/fair-lending screen** (`ecoa_audit`): disparate-impact tercile comparison on ZIP cost modifiers against supplied Census ACS minority-share data. Runs before every enterprise deployment.

### Kill list executed
- `utils/` deleted (1,168 lines, zero importers). Git history keeps the audit.
- `config.legacy.py` deleted (3,180 lines). Git is the audit diff.
- `engines/export_engine.py` (2,046 lines) quarantined in `legacy/`.
- `data/repair_estimator.db` (3.4MB committed binary) purged from the repo and git index; now `.gitignore`d.
- `engines/__init__.py` star-exports removed — explicit imports only.
- `permit_live_engine` is honest: `NO_PROVIDER_CONFIGURED` / `PROVIDER_UNSUPPORTED` instead of a stub that always said `REQUIRES_KEY`.

## Quickstart

```bash
git clone https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator.git
cd RealEstate-Repair-Cost-Estimator
python -m venv .venv
# Windows: .venv\Scripts\activate  |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# REQUIRED for share links — generate and paste into .env:
python -c "import secrets; print(secrets.token_urlsafe(48))"   # → SHARE_SECRET=...
streamlit run app.py   # → http://localhost:8501
```

Docker:

```bash
docker compose up --build        # Streamlit :8501 + FastAPI :8000 + Redis (rate limiting)
```

Agent API:

```bash
export SHARE_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
export API_KEY=your-api-key
uvicorn api_server:app --port 8000
# POST /v1/estimate_repair (Bearer auth + Idempotency-Key)
# GET  /s/{token}  ·  GET /v1/openapi.json  ·  GET /api/health  ·  GET /metrics
printf '{"method":"tools/list","id":1}\n' | python mcp_server.py
printf '{"method":"resources/list","id":2}\n' | python mcp_server.py
```

Quality gates (same as CI):

```bash
ruff check . && ruff format --check .
pytest -q
pytest -q --cov=engines.share_engine --cov=engines.audit_log --cov-fail-under=85  # …16 modules, see ci.yml
```

## Project structure

```
app.py                    # Streamlit entrypoint (progressive intake, 5-badge UI, PWA)
api_server.py             # FastAPI v1: /v1/estimate_repair, /s/{token}, /metrics, OWASP headers
mcp_server.py             # MCP: tools + resources (repair://provenance, repair://cost-tables)
config.py                 # Versioned loader over data/*.json
data/                     # Versioned datasets (config_version.json); snapshots/ + audit_log.jsonl (gitignored)
engines/                  # 35 focused modules — see below
legacy/                   # Quarantined export_engine.py (superseded by export_pdf/export_excel)
static/                   # Design system, PWA manifest, llms.txt (courtesy), openapi.json (CI-synced)
docs/                     # GEO templates, ARCHITECTURE.md
tests/                    # 82 deterministic tests: property-based badge invariant, security, MCP contract
```

### Key engines (v3.4 new + hardened)

| Module | Role |
|---|---|
| `audit_log.py` | Append-only hash-chained audit trail (SOC2 seed) |
| `observability.py` | Structured JSON logs, badge-mix metrics, VERIFIED% North Star, OTel hooks |
| `confidence_engine.py` | Signal-based calibrated finding confidence (replaces flat 0.85/0.75) |
| `citable_engine.py` | Markdown twin + JSON-LD + citation block (GEO attribution-proofing) |
| `compliance_engine.py` | EU AI Act docs + ECOA disparate-impact screen |
| `etl_engine.py` | Content-hashed, lineage-tracked data snapshots |
| `fred_engine.py` | FRED macro anchors (FEDFUNDS/HOUST/CPI-rent/PPI-construction) |
| `share_engine.py` | HMAC share tokens — required secret, rotation, timing-safe verify |
| `rate_limit.py` | Redis-backed sliding window + in-memory fallback |
| `insurance_engine.py` | Regex red-flag rules with per-flag source_url + as_of |
| `investor_engine.py` | MAO/cap-rate/CoC with fully-badged heuristic registry |
| `legal_engine.py` | Repair addenda + escrow holdbacks — ATTORNEY_REVIEW_REQUIRED hard flag |

## Data sources (official first, proxies labeled)

Census Geocoder + ACS · USGS Earthquake Catalog + Design Maps (ASCE 7-22) · FEMA NFHL ArcGIS/WMS · BLS OEWS/PPI · CPSC recalls · FRED (St. Louis Fed) · Open-Meteo (supplemental). Fallback proxies are labeled as such in provenance. Shared HTTP session: retries, backoff, timeouts, latency metrics.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — provenance contract, language rules (estimate, never "simulate"), and how to add a data source. Report issues via [GitHub Issues](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator/issues).

## Disclaimer

Informational purposes only — **not** engineering, legal, financial, or insurance advice. Estimates derive from government datasets and deterministic models; actual bids vary. Generated legal templates carry `ATTORNEY_REVIEW_REQUIRED: true` and must be reviewed by a licensed attorney. Always verify with licensed local professionals. Provided **as is**, without warranty.

## License

MIT — see [LICENSE](LICENSE).

**Dipak Jad** · [@dipakjad1993](https://github.com/dipakjad1993) · [Repository](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator)
