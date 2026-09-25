# Real Estate Repair Cost Estimator — v3.3 Enterprise

[![CI](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator/actions/workflows/ci.yml/badge.svg)](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.37-red)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> **Provenance-tracked property intelligence.** Inspection PDFs, photos, voice walkthroughs, and floorplans become transparent, deterministic repair estimates across **21+ analysis modules** — powered by live government data, with every figure badged. **Nothing is fabricated.**

## The provenance contract

Every number in this tool carries exactly one badge:

| Badge | Meaning |
|---|---|
| 🟢 **VERIFIED** | Live government data (Census · BLS · FEMA · USGS · CPSC) or evidence-backed user MLS |
| 🟡 **USER_PROVIDED** | Your quotes, MLS rows, uploads — authoritative, always wins |
| 🔵 **MODELED** | Deterministic estimate from verified baselines — **not a quote** |
| 🟠 **REQUIRES_KEY** | Live enrichment available once an API key is configured |
| ⚪ **UNAVAILABLE** | Source unreachable — reported honestly, never guessed |

Deterministic means reproducible: same inputs → same outputs, no randomness, no invented firms, licenses, permits, or comps.

## 60-second path vs deep dive

**Progressive intake** — no 7-section homework up front:

1. **Step 0 · Instant ballpark** — address + ZIP + sqft → live Census/BLS market anchor + climate v2 (wildfire / hurricane / NFIP premium impact / non-renewal risk).
2. **Deep dive** — upload the inspection PDF (parsed with PyMuPDF + `pymupdf4llm`, chunk-perfect for RAG), damage photos (Vision 2.0 → condition/system/confidence + honest *NOT-visible* list), voice notes (faster-whisper/Deepgram, optional), floorplan JSON/CSV/Matterport, contractor quotes, permit rows, sold comps.
3. **Analysis** — 21-module dossier: cost matrix, CapEx, rooms, ARV, market baseline, permits, insurance, climate, recalls, vision, voice, copilot letter.
4. **Results** — lender share link (expiring HMAC URL, redacted PII), full PDF package, Excel workbook, auditable JSON.
5. **Health** — live status + per-host latency for every data source (1h cached, loads in seconds).

## Interface (v3.3)

Apple-grade Streamlit design system (`static/style.css`, self-hosted **Google Sans Flex** — the 2026 Pixel system typeface, optical sizing on — frosted-glass sticky nav, true-black dark mode via `?theme=dark` or the nav toggle):

- One H1 per page (hero headers; enforced by test), numbered section rhythm across the intake form, Step-0 ballpark as a hero card — not a buried expander.
- Type-to-edit numeric fields (no clunky steppers), card-style metrics, segmented pill tabs, dashed-dropzone uploaders, copy-friendly share-link blocks.
- Health renders a real status table (Operational / Needs API key / Unreachable + checked timestamps) instead of raw debug lines.
- PDF export sanitizes inspection unicode (em-dashes, bullets, arrows) so the lender package never crashes on real-world text.
- Mobile-first PWA CSS + web manifest — 70% of walkthroughs happen on a phone in a crawlspace.
- Theme-safe tables everywhere: Streamlit's grid paints on `<canvas>` (ignores CSS, stays white in dark mode), so all read-only tables render as theme-aware HTML (sticky headers, tabular numerals, severity-tinted alerts). Sandbox picker uses native checkboxes, not a grid editor — dark mode is fully audited light + dark via Playwright screenshots.

## Quickstart

```bash
git clone https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator.git
cd RealEstate-Repair-Cost-Estimator
python -m venv .venv
# Windows: .venv\Scripts\activate  |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add keys to unlock live enrichment (optional)
streamlit run app.py   # → http://localhost:8501
```

Docker:

```bash
docker compose up --build        # Streamlit :8501 + FastAPI :8000
```

Agent API:

```bash
uvicorn api_server:app --port 8000
# POST /api/estimate_repair · GET /s/{token} · GET /api/openapi.json · GET /llms.txt
printf '{"method":"tools/list","id":1}\n' | python mcp_server.py
```

Quality gates (same as CI):

```bash
ruff check . && ruff format --check .
pytest -q
```

## What the engine does

| Module | Source of truth |
|---|---|
| Cost matrix (DIY / contractor / emergency) | BLS OEWS trade wages + BLS PPI materials + state multipliers, 24h cached |
| Room-by-room | Good/Fair/Poor/Gut + Low/Mid/High + Immediate (<30d) / 6-mo / 12-mo / Deferred |
| ARV + rents | Distance/recency/DOM-weighted sold comps; Attom/RentCast/BatchData key-gated, honest fallback |
| Market baseline (per trade) | `estimate_market_baseline()` — USER_QUOTE wins, else BLS baseline + margin |
| Permits | User portal rows (authoritative) + BuildFax/Echelon key-gated + retroactive cost/timeline |
| Insurance + climate v2 | Red flags, denial probability, premium impact, non-renewal risk (2026 FL/CA headlines) |
| Recalls | Live CPSC SaferProducts.gov cross-reference |
| CapEx 24-mo | Depreciation tables (versioned) + failure probabilities |
| Negotiation copilot | Cited offer-credit letter from sandbox + leverage + DOM |
| Vision 2.0 | Photo → condition/system/confidence; YOLOv8-seg + multimodal LLM key-gated |
| Voice | faster-whisper/Deepgram (default OFF — no 1GB download), diarization heuristic, transcript→finding link |
| Exports + sharing | Lazy PDF/Excel/JSON + expiring lender share portal |

## Data sources (official first, proxies labeled)

Census Geocoder + ACS · USGS Earthquake Catalog + Design Maps (ASCE 7-22) · FEMA NFHL ArcGIS/WMS · BLS OEWS/PPI · CPSC recalls · Open-Meteo (supplemental). `floodzonemap.org`, `faultlinemap.com`, Nominatim are **fallback-only** and labeled as such in provenance. Shared session: retries, backoff, timeouts, latency metrics.

Cost/config tables live versioned in `data/*.json` (`data/config_version.json`); `config.py` is a thin loader (`config.legacy.py` preserved for audit). PII is redacted in logs, vaulted with TTL; persistence is Supabase/RLS with sqlite fallback; per-key rate limits on runs and API.

## Project structure

```
app.py                    # Streamlit entrypoint (progressive intake, 5-badge UI, PWA)
api_server.py             # FastAPI: /api/estimate_repair, /s/{token}, /api/openapi.json
mcp_server.py             # MCP: repair-estimator-mcp (estimate_repair tool for agents)
config.py                 # Versioned loader over data/*.json
data/                     # Versioned datasets (config_version.json)
engines/                  # 30 focused modules (cost, rooms, comps, climate, permits,
                          #   insurance, recalls, vision, voice, copilot, share, exports…)
static/                   # Apple-style design system, PWA manifest, llms.txt, openapi.json
docs/                     # GEO templates (/repair-cost/{state}/{system}/), ARCHITECTURE.md
tests/                    # Deterministic pytest suite (no live network)
```

## GEO / agent visibility

Next.js-ready MDX template (`docs/repair-cost/_template.mdx`): 50-word answer capsule, Low/Mid/High HTML table, FAQPage + Article schema. `static/llms.txt` invites agent traffic (GPTBot/ClaudeBot/PerplexityBot allowed). Track AI mention rate, citation rate, share of voice, agent-initiated estimates, PDF shares → offers accepted.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — provenance contract, language rules (estimate, never "simulate"), and how to add a data source. Report issues via [GitHub Issues](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator/issues).

## Disclaimer

Informational purposes only — **not** engineering, legal, financial, or insurance advice. Estimates derive from government datasets and deterministic models; actual bids vary. Always verify with licensed local professionals. Provided **as is**, without warranty.

## License

MIT — see [LICENSE](LICENSE).

**Dipak Jad** · [@dipakjad1993](https://github.com/dipakjad1993) · [Repository](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator)
