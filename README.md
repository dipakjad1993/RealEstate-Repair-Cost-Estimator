# Real Estate Repair Cost Estimator

> **A provenance-tracked property analysis platform.** Turns inspection reports, photos, audio, and floorplans into transparent repair cost estimates across **21 analysis modules** — using real, verifiable government data and fully deterministic calculations. **Nothing is fabricated.**

Built with Streamlit, styled like an Apple product: a disciplined design system with Inter typography, frosted-glass navigation, dark/light themes, and a focus on readability.

---

## Why it's different

| | Typical estimator | This platform |
|---|---|---|
| **Numbers** | Random, generic averages | Deterministic + real data |
| **Sources** | Opaque | Every figure carries a **provenance badge** |
| **Scope** | Basic cost list | 21 cross-referenced modules |
| **Output** | One number | Verified, auditable, exportable |

### Provenance badges
Every value in the tool is labeled — there are no silent guesses:

- 🟢 **VERIFIED** — live government data (Census · BLS · FEMA · USGS · CPSC)
- 🟡 **USER-PROVIDED** — your quotes, MLS data, uploaded documents
- 🟠 **REQUIRES KEY** — needs an API key for live enrichment
- 🔵 **MODELED** — deterministic estimate, clearly not a quote
- ⚪ **UNAVAILABLE** — honestly reported when a source can't be reached

---

## Features

### Verified data pipeline
- **Live fetchers** for Census, BLS wages, FEMA flood zones, USGS seismic hazards, and CPSC product recalls — with graceful degradation and honest health reporting when a source is unreachable.
- **BLS-wage baselines** for labor costs and **state-specific** permit fees, taxes, and market anchors.
- **Audio transcription** (Whisper) so voice notes from inspections become structured findings.

### 21 analysis modules
1. **Parse** — extraction from PDF reports (pdfplumber / PyMuPDF)
2. **Cost** — itemized material / labor / overhead / profit with confidence intervals
3. **Depreciation** — component-by-component schedules and remaining life
4. **Market** — price-per-sqft anchors, comparables, trend analysis
5. **Export** — PDF / Excel / JSON deliverables
6. **Vision** — evidence summary and photo-to-finding matching
7. **Permits** — 50-state fee database, unpermitted-work detection, retroactive guidance
8. **CapEx (24-mo)** — replacement timeline with failure probabilities
9. **Sandbox** — sellers-credit negotiation scenarios with a live data editor
10. **Dispatch** — prioritization and urgency ordering
11. **Legal** — repair addenda and escrow holdback agreements
12. **Environmental** — flood, seismic, wildfire, and soil risk with mitigation
13. **Brokerage** — agent performance and brokerage ROI
14. **Lead magnet** — listing-ready summaries
15. **Insurance** — insurability score and premium impact
16. **Investor** — ARV, NOI, cap rate, cash-on-cash, risk scores
17. **Escrow** — milestone-based holdback structures
18. **SEO** — listing optimization and analytics
19. **Audio** — Whisper transcription workflow
20. **Recalls** — CPSC cross-referenced recall checks
21. **Spatial** — floor-plan flaw mapping (JSON/CSV/Matterport)

### Premium UI / UX
- **Apple-inspired design system** — strict type/spacing/radius/shadow scale, self-hosted **Inter** variable font, hairline borders, single accent color.
- **Frosted-glass floating navigation** with live status indicator.
- **Dark / Light themes** that persist in the URL (`?theme=dark`) and recolor every component, table, and chart.
- **Page hero headers**, segmented-control tabs, metric cards, framed tables and charts.

---

## Getting started

### Prerequisites
- Python 3.10+ (tested on 3.13)
- pip

### Install & run
```bash
git clone https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator.git
cd RealEstate-Repair-Cost-Estimator
python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Open **http://localhost:8501**.

### Workflow
1. **Inputs** — enter the address + property profile, paste contractor quotes and permits, upload inspection PDFs, photos, audio, a floorplan (JSON/CSV/Matterport URL), or a closed-deal CSV. Press **Run Analysis**.
2. **Analysis** — review the 21 modules, each with source badges.
3. **Results** — verified summaries, CapEx timeline, negotiation sandbox, legal documents, and exports.
4. **Health** — live status of every data source.

### Optional API keys
Create `.env` (or set secrets) to unlock live enrichment:

```
CENSUS_API_KEY=your_key_here
FEMA_API_KEY=your_key_here
USGS_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

Without keys, the tool still runs — it labels enriched values `REQUIRES_KEY` instead of guessing.

---

## Architecture

```
Streamlit app.py
   ├── Navigation + theme (frosted glass, dark/light, URL-persisted)
   ├── Inputs  ── ingestion_engine.py  (validate, import, transcribe)
   ├── Analysis ── analysis_engine.py   (orchestrates 21 modules)
   ├── Results ── 21 renderers + exports
   └── Health  ── real_data_fetcher.check_api_health()

engines/ (each a focused, testable unit)
   real_data_fetcher.py   live Census/BLS/FEMA/USGS/CPSC
   cost_engine.py · capex_engine.py · market_engine.py · permit_engine.py
   environmental_engine.py · insurance_engine.py · investor_engine.py
   recall_engine.py · roi_engine.py · legal_engine.py · seo_engine.py
   spatial_engine.py · sandbox_engine.py · contractor_engine.py
   depreciation_engine.py · parser_engine.py · cv_engine.py
   export_engine.py · voice_engine.py · ingestion_engine.py · analysis_engine.py
```

### Design system
`static/style.css` defines the full palette (light `#F5F5F7` + dark `#000` tokens), and `static/fonts/Inter-VF.woff2` is the self-hosted, offline-safe font. The theme is applied by Streamlit state, mirrored to the URL, and enforced in CSS — no element falls back to framework defaults.

---

## Configuration

Key settings live in:

| File | Purpose |
|------|---------|
| `config.py` | Market anchors, thresholds, cost baselines |
| `.streamlit/config.toml` | Server, static serving, base theme |
| `requirements.txt` | Runtime dependencies |

---

## Data sources

| Source | Used for |
|--------|----------|
| **US Census** | Housing statistics, market anchors |
| **BLS** | Occupational wage baselines for labor |
| **FEMA NFHL** | Flood zone designations |
| **USGS** | Seismic hazard / peak ground acceleration |
| **CPSC** | Product recall cross-referencing |
| **CAL FIRE / USDA** | Wildfire severity and soil classification |

All calculations are deterministic (hash-seeded, formula-based) — the same input always produces the same output, and no `random` module is used.

---

## Project structure

```
RealEstate-Repair-Cost-Estimator/
├── app.py                      # Streamlit entrypoint (UI, nav, theme)
├── config.py                   # Baselines & configuration
├── requirements.txt
├── .streamlit/config.toml
├── engines/                    # 22 engine modules (see Architecture)
├── static/
│   ├── style.css               # Premium Apple-inspired design system
│   └── fonts/Inter-VF.woff2    # Self-hosted Inter variable font
├── templates/                  # Export templates
├── utils/                      # Shared helpers
└── data/                       # Local data artifacts
```

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit, Plotly |
| Data | Pandas, NumPy |
| Document parsing | pdfplumber, PyMuPDF |
| Audio | openai-whisper |
| Live data | requests (Census, BLS, FEMA, USGS, CPSC) |
| Styling | Custom CSS design system (Inter typeface) |

---

## Disclaimer

This tool is for **informational purposes only** and is **not** a substitute for licensed inspectors, contractors, insurance agents, real estate agents, attorneys, or financial advisors. Estimates derive from regional averages, government datasets, and deterministic models — always verify with local professionals before making decisions. Provided **as is**, without warranty.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contact

**Dipak Jad** · [@dipakjad1993](https://github.com/dipakjad1993) · [Repository](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator)

Issues, questions, and feature requests are welcome via [GitHub Issues](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator/issues).