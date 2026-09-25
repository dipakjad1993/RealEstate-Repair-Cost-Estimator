# Architecture (enterprise)

```
Browser/PWA (/app) ── Streamlit app.py (progressive intake, 5-badge UI)
Agents ── FastAPI api_server.py (/api/estimate_repair, /s/{token}) + mcp_server.py
Docs/GEO ── Next.js/MDX under docs/repair-cost/{state}/{system}/ + static/llms.txt

Engines (deterministic, provenance-tagged):
 ingestion -> parser (PyMuPDF+pymupdf4llm) -> cost (BLS wages/PPI + state mult)
 -> capex -> market -> comps (Attom/RentCast/key-gated) -> rooms
 -> contractor estimate_market_baseline (USER_QUOTE wins)
 -> permit check_permit_compliance + live layer -> insurance + climate v2
 -> recalls (CPSC live) -> vision v2 -> voice_nlp -> negotiation copilot
 -> export (lazy pdf/excel/json) -> share (HMAC) -> db_supabase (RLS)

Gov data: gov_sources_v2 (official-first) over http_client (retries/backoff/latency).
Config: data/*.json versioned (config.py is a loader).
PII: pii_vault redaction + TTL vault. Rate limits: rate_limit.py.
```

Measurement that matters: AI mention rate, citation rate, share of voice vs
comps, agent-initiated estimates, PDF shares -> offers accepted.
