"""
Real Estate Repair Cost Estimator - v3.1 ENTERPRISE (provenance-tracked)
=======================================================================
Progressive intake: Address only -> instant ballpark -> deep dive after PDF.
PIPELINE: ingestion -> gov data (official-first) -> deterministic cost
(BLS wages/PPI + state mult) -> rooms/comps/climate/permits/insurance/
recalls/vision/voice -> negotiation copilot -> lender share + exports.

Provenance brand (H1/meta/schema): every value carries exactly one of
VERIFIED | USER_PROVIDED | MODELED | REQUIRES_KEY | UNAVAILABLE.
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Portable import bootstrap: repo root on sys.path without hardcoded OS paths.
# Works on Streamlit Cloud / Docker / Linux / Windows.
_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engines.analysis_engine import generate_deep_analysis
from engines.capex_engine import generate_capex_horizon
from engines.contractor_engine import (
    estimate_market_baseline,
    get_contractor_recommendations,
)
from engines.cost_engine import RealRates, generate_cost_matrix
from engines.environmental_engine import (
    assess_environmental_risks,
)
from engines.ingestion_engine import (
    STATE_ABBREV,
    compile_session_input,
    validate_zip9,
)
from engines.insurance_engine import (
    analyze_insurance_risk,
    calculate_insurance_scorecard,
)
from engines.investor_engine import analyze_investor_deal
from engines.legal_engine import (
    generate_escrow_holdback_agreement,
    generate_legal_addendum,
)
from engines.market_engine import (
    generate_market_profile,
    generate_negotiation_strategies,
)
from engines.permit_engine import (
    check_permit_compliance,
    cross_reference_findings_with_permits,
    extract_permit_needs_from_findings,
)
from engines.pii_vault import vault_store
from engines.rate_limit import GLOBAL_LIMITER
from engines.real_data_fetcher import check_api_health
from engines.recall_engine import check_recalls_for_findings
from engines.roi_engine import generate_brokerage_roi_data
from engines.sandbox_engine import (
    calculate_sandbox_totals,
    create_sandbox_session,
    generate_scenario_comparison,
)
from engines.seo_engine import (
    generate_seo_landing_pages,
)
from engines.spatial_engine import create_spatial_map

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Repair Cost Estimator v3",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Canonical 5-badge provenance system (enterprise trust contract).
# Everything maps to these five. Clarity = trust = citations.
# VERIFIED: live gov data (Census/BLS/FEMA/USGS/CPSC) or user MLS w/ evidence
# USER_PROVIDED: quotes, MLS, uploads supplied by the user (authoritative)
# MODELED: deterministic estimate from verified baselines, NOT a quote
# REQUIRES_KEY: live enrichment available once an API key is configured
# UNAVAILABLE: source unreachable — reported honestly, never guessed
BADGE_STYLES = {
    "VERIFIED": ("🟢", "VERIFIED"),
    "USER_PROVIDED": ("🟡", "USER-PROVIDED"),
    "MODELED": ("🔵", "MODELED (not a quote)"),
    "REQUIRES_KEY": ("🟠", "REQUIRES API KEY"),
    "UNAVAILABLE": ("⚪", "UNAVAILABLE"),
}
# Legacy aliases collapse to the canonical five (back-compat for old engines).
BADGE_ALIASES = {
    "USER_MLS_VERIFIED": "VERIFIED",
    "USER_QUOTE": "USER_PROVIDED",
    "BENCHMARK_REAL": "VERIFIED",
    "BLS_WAGE_BASELINE": "VERIFIED",
    "USER_FLOORPLAN": "USER_PROVIDED",
    "USER_MATTERPORT": "USER_PROVIDED",
    "USER_TRANSACTION_IMPORT": "USER_PROVIDED",
    "USER_ANALYTICS": "USER_PROVIDED",
    "TEMPLATE": "MODELED",
    "MODELED_BENCHMARK": "MODELED",
    "IMAGE": "MODELED",
    "BENCHMARK": "MODELED",
}


def badge(status):
    canon = BADGE_ALIASES.get(status, status)
    icon, label = BADGE_STYLES.get(canon, ("⚪", canon or "UNKNOWN"))
    return f"{icon} **{label}**"


def canonical_badge(status):
    """Collapse any legacy badge to the canonical five."""
    return (
        BADGE_ALIASES.get(status, status)
        if status in BADGE_STYLES or status in BADGE_ALIASES
        else (status or "UNAVAILABLE")
    )


def provenance_col(status, source=""):
    src = f"<span style='color:#888;font-size:0.8em'> {source}</span>" if source else ""
    return f"{badge(status)}{src}"


def money(v):
    try:
        return f"${float(v):,.0f}"
    except (TypeError, ValueError):
        return "—"


def section(number: str, title: str, sub: str = ""):
    """Numbered enterprise section header with consistent rhythm."""
    sub_html = f"<div class='section-sub'>{sub}</div>" if sub else ""
    st.markdown(
        f"<div class='form-section'><div class='section-eyebrow'>Section {number}</div>"
        f"<div class='section-title'>{title}</div>{sub_html}</div>",
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------
# Theme + CSS injection
# ------------------------------------------------------------------
def load_css():
    css = Path(__file__).resolve().parent / "static" / "style.css"
    st.markdown(f"<style>{css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def apply_theme():
    """CSP-safe theming. No JS injection, no st.iframe hacks.

    Uses native Streamlit theme context when available (st.context.theme)
    and mirrors the choice to CSS vars via [data-theme] on our own
    components + ?theme= query param. Streamlit strips <script> and
    blocks window.parent access under CSP, so the old iframe approach
    is retired.
    """
    theme = st.session_state.get("theme", "light")
    try:
        ctx_theme = None
        if hasattr(st, "context") and hasattr(st.context, "theme"):
            ctx_theme = st.context.theme
            # st.context.theme.type is 'dark' | 'light' on newer runtimes
            t = getattr(ctx_theme, "type", None) or getattr(ctx_theme, "base", None)
            if t in ("dark", "light") and "theme" not in st.session_state:
                theme = t
                st.session_state["theme"] = t
    except Exception:
        pass
    # CSS-var hook: our style.css keys off :root and [data-theme="dark"].
    st.markdown(
        f"<div data-theme='{theme}' data-theme-hook='active' style='display:none' aria-hidden='true'></div>",
        unsafe_allow_html=True,
    )
    return theme


def render_theme_toggle():
    """Dark/Light toggle driven by a real Streamlit widget (guaranteed to
    trigger a rerun — Streamlit strips inline JS from HTML, so we avoid it)."""
    current = st.session_state.get("theme", "light")
    try:
        choice = st.segmented_control(
            "Appearance",
            ["Dark", "Light"],
            default="Light" if current == "light" else "Dark",
            key="theme_control",
        )
        new = "dark" if choice == "Dark" else "light"
    except Exception:
        c1, c2 = st.columns(2)
        if c1.button(
            "🌙",
            use_container_width=True,
            type="primary" if current == "dark" else "secondary",
            key="btn_theme_dark",
        ):
            st.session_state["theme"] = "dark"
            st.query_params["theme"] = "dark"
            st.rerun()
        if c2.button(
            "☀️",
            use_container_width=True,
            type="primary" if current == "light" else "secondary",
            key="btn_theme_light",
        ):
            st.session_state["theme"] = "light"
            st.query_params["theme"] = "light"
            st.rerun()
        return
    if new != current:
        st.session_state["theme"] = new
        st.query_params["theme"] = new


def theme_plotly(fig):
    """Apply the active theme to a Plotly figure so charts match the app
    (transparent background, themed text/grid, clean colorway)."""
    dark = st.session_state.get("theme", "light") == "dark"
    text = "#F5F5F7" if dark else "#1D1D1F"
    grid = "rgba(255, 255, 255, 0.12)" if dark else "rgba(0, 0, 0, 0.07)"
    fig.update_layout(
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font=dict(family="Inter, -apple-system, 'Segoe UI', sans-serif", color=text),
        title_font_color=text,
        colorway=["#0071E3", "#5AC8FA", "#FF9F0A", "#FF375F", "#32D74B", "#BF5AF2", "#FFD60A", "#64D2FF"],
        hoverlabel=dict(
            bgcolor="#1D1D1F" if not dark else "#F5F5F7",
            font=dict(color="#F5F5F7" if not dark else "#1D1D1F"),
        ),
        xaxis=dict(gridcolor=grid),
        yaxis=dict(gridcolor=grid),
    )
    return fig


# ------------------------------------------------------------------
# Navigation
# ------------------------------------------------------------------
NAV = [
    ("Inputs", "🖊️", "Inputs"),
    ("Analysis", "🔬", "Analysis"),
    ("Results", "📊", "Results"),
    ("Health", "🩺", "Health"),
]
NAV_TITLES = {
    "Inputs": "Input & Property Intake",
    "Analysis": "Deep Analysis & Research",
    "Results": "Verified Results",
    "Health": "Data Source Health",
}

PAGE_HERO = {
    "Inputs": (
        "Property Intelligence",
        "Input & Property Intake",
        "Feed verified property data, inspection reports, and market context. "
        "Every field feeds a provenance-tracked pipeline.",
    ),
    "Analysis": (
        "Deep Research",
        "Deep Analysis & Research",
        "Twenty-two cross-referenced modules — cost, capEx, market, permits, "
        "insurance, recalls, spatial, legal, ROI and more.",
    ),
    "Results": (
        "Verified Output",
        "Verified Results",
        "Every figure carries a source badge: VERIFIED, USER-PROVIDED, "
        "MODELED, or UNAVAILABLE. Nothing is fabricated.",
    ),
    "Health": (
        "System Integrity",
        "Data Source Health",
        "Live status of every government data source powering your estimates.",
    ),
}


def render_top_nav():
    current = st.session_state.get("page", "Inputs")
    with st.container(border=True):
        brand, nav, theme = st.columns([1.8, 2.4, 1.0], vertical_alignment="center", gap="medium")
        with brand:
            st.markdown(
                """
            <div class="prem-brand">
              <span class="prem-logo">◈</span>
              <div class="prem-brand-text">
                <div class="prem-brand-title">Repair Estimator</div>
                <div class="prem-brand-sub"><span class="status-dot"></span>Property Intelligence · Verified</div>
              </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with nav:
            cols = st.columns(len(NAV), gap="small")
            for i, (key, icon, label) in enumerate(NAV):
                with cols[i]:
                    if key == current:
                        st.markdown(
                            f'<div class="prem-nav-item active">'
                            f'<span class="nav-ic">{icon}</span>{label}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        if st.button(label, key=f"nav_{key}", use_container_width=True, type="secondary"):
                            st.session_state["page"] = key
                            st.rerun()
        with theme:
            render_theme_toggle()
    return current


def render_footer():
    st.markdown(
        """
    <div class="app-footer">
      <span class="footer-emblem">◈</span>
      Every figure is derived from real, verified government data
      (Census · BLS · FEMA · USGS · CPSC) or honestly labeled
      MODELED / UNAVAILABLE. Nothing is fabricated.
    </div>
    """,
        unsafe_allow_html=True,
    )


def page_header(page):
    """Premium hero header shown above every page's content."""
    kicker, title, subtitle = PAGE_HERO.get(page, PAGE_HERO["Inputs"])
    st.markdown(
        f"""
    <div class="page-hero">
      <div class="hero-kicker">{kicker}</div>
      <h1 class="hero-title">{title}</h1>
      <div class="hero-sub">{subtitle}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------
# Pipeline (cached gov baselines: 24h TTL; deterministic assembly)
# ------------------------------------------------------------------
@st.cache_data(ttl=86400, show_spinner=False)
def _cached_market(zip_code, state, mls_json):
    import json as _j

    from engines.market_engine import generate_market_profile as _gmp

    return _gmp(zip_code, state, _j.loads(mls_json))


@st.cache_data(ttl=86400, show_spinner=False)
def _cached_health():
    from engines.real_data_fetcher import check_api_health as _h

    return _h()


@st.cache_data(ttl=3600, show_spinner="Probing live data sources…")
def _cached_detailed_health():
    from engines.gov_sources_v2 import detailed_health as _dh

    return _dh()


def run_pipeline(session):
    pd_ = session["property_data"]
    mls = session["mls"]
    uw = session["underwriting"]
    quotes = session["quotes"]
    permits = session["permits"]
    findings = session["findings"]
    floorplan = session["floorplan"]

    rates = RealRates(pd_["state"], pd_["zip_code"])
    cost_matrix = generate_cost_matrix(findings, pd_["state"], pd_["zip_code"], quotes, rates)
    capex = generate_capex_horizon(findings, pd_)
    market = generate_market_profile(pd_["zip_code"], pd_["state"], mls)
    env = assess_environmental_risks(pd_, findings)
    bids = estimate_market_baseline(findings, pd_["zip_code"], cost_matrix, pd_["state"], quotes)
    insurance = analyze_insurance_risk(findings, pd_, uw)
    insurance_scorecard = calculate_insurance_scorecard(findings, pd_, uw)
    recalls = check_recalls_for_findings(findings)
    spatial = create_spatial_map(findings, pd_, floorplan.get("rooms", []))
    investor = analyze_investor_deal(pd_, findings, cost_matrix, capex, market, uw)
    legal = generate_legal_addendum(pd_, findings, cost_matrix)
    permit_result = check_permit_compliance(pd_, permits)
    permit_xref = cross_reference_findings_with_permits(findings, permits)
    permit_needs = extract_permit_needs_from_findings(findings)
    seo = generate_seo_landing_pages(pd_["zip_code"], cost_matrix)
    brokerage = generate_brokerage_roi_data("", session.get("transactions"))
    sandbox = create_sandbox_session(pd_, findings, cost_matrix)
    strategies = generate_negotiation_strategies(findings, market, pd_)
    health = check_api_health()

    # leverage score from real MLS signals
    leverage = 50
    if mls.get("dom") is not None:
        leverage = 30 if mls["dom"] > 60 else 55 if mls["dom"] > 40 else 70
    if market.get("market_position") == "ABOVE_ZIP_MEDIAN":
        leverage = max(leverage, 65)

    results = {
        "rates": rates,
        "cost_matrix": cost_matrix,
        "capex": capex,
        "market": market,
        "environmental": env,
        "bids": bids,
        "insurance": insurance,
        "insurance_scorecard": insurance_scorecard,
        "recalls": recalls,
        "spatial": spatial,
        "investor": investor,
        "legal": legal,
        "permit": permit_result,
        "permit_xref": permit_xref,
        "permit_needs": permit_needs,
        "seo": seo,
        "brokerage": brokerage,
        "sandbox": sandbox,
        "strategies": strategies,
        "health": health,
        "leverage": leverage,
        "generated_at": datetime.now().isoformat(),
    }
    # ---- 2026 enterprise extensions (deterministic, provenance-tagged) ----
    try:
        from engines.room_engine import rate_rooms as _rate_rooms

        cost_by = {}
        for it in cost_matrix.get("line_items", []):
            cost_by[it.get("finding_key", it.get("finding", ""))] = {
                "low": it.get("total_low", 0),
                "mid": it.get("total_avg", 0),
                "high": it.get("total_high", 0),
            }
        # attach location-aware keys for room mapping
        findings_loc = [{**f, "location": f.get("location", "General")} for f in findings]
        results["rooms"] = _rate_rooms(findings_loc, cost_by)
    except Exception as e:
        results["rooms"] = {"error": str(e)[:160]}
    try:
        from engines.comps_engine import estimate_arv as _arv

        results["arv_comps"] = _arv(
            session.get("comps") or [],
            subject_sqft=pd_.get("square_footage", 0),
            list_price=(mls.get("list_price") or uw.get("arv")),
        )
    except Exception as e:
        results["arv_comps"] = {"provenance": "UNAVAILABLE", "error": str(e)[:160]}
    try:
        from engines.climate_engine_v2 import assess_climate_v2 as _clim

        flags = {
            "wildfire": any("fire" in str(f.get("description", "")).lower() for f in findings),
            "foundation": any("foundation" in str(f.get("description", "")).lower() for f in findings),
        }
        fz = ((env.get("flood") or {}) if isinstance(env, dict) else {}).get("flood_zone", "X")
        results["climate_v2"] = _clim(
            pd_.get("state", ""), fz=fz if isinstance(fz, str) else "X", finding_flags=flags
        )
    except Exception as e:
        results["climate_v2"] = {"error": str(e)[:160]}
    try:
        from engines.negotiation_copilot import draft_offer_credit as _draft

        items = [
            {
                "system": b.get("system"),
                "severity": b.get("severity"),
                "finding": b.get("finding"),
                "bid_high": b.get("bid_high"),
            }
            for b in bids.values()
        ]
        results["offer_copilot"] = _draft(
            items,
            leverage=leverage,
            dom=(mls.get("dom") or 0),
            address=pd_.get("address", "Subject Property"),
        )
    except Exception as e:
        results["offer_copilot"] = {"error": str(e)[:160]}
    try:
        from engines.vision_engine_v2 import analyze_photos_v2 as _vis

        results["vision_v2"] = _vis(session.get("photos") or [], findings)
    except Exception as e:
        results["vision_v2"] = {"error": str(e)[:160]}
    try:
        from engines.pii_vault import redact_dict as _red
        from engines.share_engine import seal_snapshot as _seal

        results["share_token"] = _seal(
            _red(
                {
                    "zip": pd_.get("zip_code"),
                    "state": pd_.get("state"),
                    "totals": cost_matrix.get("summary", {}),
                }
            )
        )
    except Exception:
        results["share_token"] = None
    results["deep_analysis"] = generate_deep_analysis(session, results)
    return results


# ------------------------------------------------------------------
# Page 1 - Inputs
# ------------------------------------------------------------------
def page_inputs():
    st.caption(
        "Every output is derived from **real, verified data** (Census · BLS · FEMA · USGS · CPSC) "
        "or honestly labeled MODELED / UNAVAILABLE. Nothing is fabricated. "
        "PII (address/APN) is redacted in logs and vaulted with TTL."
    )
    st.markdown("<link rel='manifest' href='/app/static/manifest.webmanifest'>", unsafe_allow_html=True)

    # ---- STEP 0 · Progressive intake: address-only instant ballpark (60s) ----
    with st.container(border=True):
        st.markdown(
            "<div class='section-eyebrow'>Step 0 · 60 seconds</div>"
            "<div class='section-title'>Instant ballpark — address only</div>"
            "<div class='section-sub'>Live market anchor + climate risk. No homework, no upload.</div>",
            unsafe_allow_html=True,
        )
        with st.form("quick_form"):
            q1, q2, q3, q4 = st.columns(4)
            with q1:
                q_addr = st.text_input("Address", placeholder="1234 Maple Ave", key="q_addr")
            with q2:
                q_state = st.selectbox("State", sorted(STATE_ABBREV), index=4, key="q_state")
            with q3:
                q_zip = st.text_input("ZIP", placeholder="90210", key="q_zip")
            with q4:
                q_sqft = st.number_input("Sqft", 200, 20000, 1800, key="q_sqft")
            if st.form_submit_button("Get ballpark", use_container_width=True):
                if not GLOBAL_LIMITER.allow("quick"):
                    st.error("Rate limit — try again in a minute.")
                elif q_zip and q_state:
                    with st.spinner("Pulling Census/BLS/climate baselines…"):
                        try:
                            from engines.climate_engine_v2 import assess_climate_v2
                            from engines.market_engine import generate_market_profile

                            m = generate_market_profile(
                                q_zip[:5], q_state, {"sqft": q_sqft, "address": q_addr}
                            )
                            c = assess_climate_v2(q_state)
                            st.success(f"Market anchor: **{m.get('anchor_description', '—')}**")
                            st.info(
                                f"Climate: wildfire {c['wildfire_score']} · hurricane {c['hurricane_score']} · "
                                f"ice {c['ice_dam_score']} · non-renewal **{c['non_renewal_risk']}** · "
                                f"indicated premium impact **${c['premium_impact']:,.0f}/yr**."
                            )
                            st.caption(
                                "Deep-dive ranges unlock after you run the full analysis below. "
                                "70% of walkthroughs happen on phone — this page is mobile-first PWA-ready."
                            )
                        except Exception as e:
                            st.error(f"Ballpark failed: {e}")
                else:
                    st.warning("Enter ZIP + state for a ballpark.")

    with st.form("input_form"):
        section("1", "Property Metadata", "Required — address identity for verification-grade lookups.")
        c1, c2, c3 = st.columns(3)
        with c1:
            addr = st.text_input("Street address", placeholder="e.g. 1234 Maple Ave")
            city = st.text_input("City", placeholder="e.g. Beverly Hills")
            state = st.selectbox("State", sorted(STATE_ABBREV), index=4)
        with c2:
            zip9 = st.text_input(
                "9-digit ZIP (ZIP+4)",
                placeholder="90210-4801",
                help="Required for verification-grade Census/BLS/FEMA lookups",
            )
            apn = st.text_input("APN (Assessor Parcel Number)", placeholder="e.g. 44-33-12-08-1024")
            ptype = st.selectbox(
                "Property type",
                ["Single Family", "Condo", "Townhouse", "Multi-Family", "Manufactured", "Other"],
            )
        with c3:
            beds = st.number_input("Bedrooms", 0, 20, 3)
            baths = st.number_input("Bathrooms", 0.0, 20.0, 2.0, 0.5)
            sqft = st.number_input("Square footage", 100, 50000, 1800)
            year_built = st.number_input("Year built", 1800, 2026, 1995)

        section("2", "Market & Geospatial Feeds", "MLS context — highest-authority market anchor.")
        c1, c2, c3 = st.columns(3)
        with c1:
            list_price = st.number_input("List price ($)", 0, 100_000_000, 0, 1000)
            price_psf = st.number_input("Price / sqft ($)", 0.0, 50000.0, 0.0)
            dom = st.number_input("Days on market", 0, 5000, 0)
        with c2:
            last_sale = st.number_input("Last sale price ($)", 0, 100_000_000, 0, 1000)
            mls_zone = st.text_input("MLS zone / tract", placeholder="e.g. C08")
            mls_source = st.text_input("MLS source (e.g. CRMLS, Bright MLS)")
        with c3:
            st.caption("Verified live feeds enabled automatically")
            st.write("✔ Census ACS (zip median value/rent) · ✔ USGS seismic/earthquakes")
            st.write("✔ FEMA flood zone · ✔ CPSC recalls · ✔ Open-Meteo · ✔ BLS wages/PPI")

        section("3", "Price & Underwriting", "Deal math inputs for investor mode.")
        c1, c2, c3 = st.columns(3)
        with c1:
            premium = st.number_input("Carrier annual premium quote ($)", 0, 1_000_000, 0, 100)
            arv = st.number_input("After-repair value ($)", 0, 100_000_000, 0, 1000)
        with c2:
            interest_rate = st.number_input("Interest rate (%)", 0.0, 30.0, 7.0, 0.1)
            monthly_rent = st.number_input("Expected monthly rent ($)", 0, 100_000, 0, 50)
        with c3:
            holding_months = st.number_input("Holding months", 1, 24, 6)

        section("4", "Contractor Quotes", "Optional — pasted quotes always win over baselines.")
        st.caption("Paste rows as: finding_key | contractor | license | low | high | eta_days")
        quotes_txt = st.text_area(
            "One quote per line",
            height=90,
            placeholder="heat exchanger crack | A1 HVAC LLC | CA-123456 | 1800 | 2600 | 5",
        )

        section("5", "Permit Records", "Copied from the county/city portal — never fabricated.")
        st.caption("Paste rows as: permit_type | permit_number | date | status | description")
        permits_txt = st.text_area(
            "One permit per line",
            height=90,
            placeholder="Electrical Permit | EL-2021-4412 | 2021-03-15 | Closed | Panel upgrade",
        )

        section("6", "Evidence Uploads", "PDF reports, damage photos, voice notes, floorplans.")
        c1, c2 = st.columns(2)
        with c1:
            pdfs = st.file_uploader(
                "Inspection report(s) (PDF)",
                type=["pdf"],
                accept_multiple_files=True,
                help="Parsed with PyMuPDF + pymupdf4llm (chunk-perfect for RAG).",
            )
            photos = st.file_uploader(
                "Damage / nameplate photos",
                type=["png", "jpg", "jpeg"],
                accept_multiple_files=True,
                help="Vision 2.0 maps each photo to system + condition + confidence.",
            )
        with c2:
            audios = st.file_uploader(
                "Audio walkthrough (faster-whisper/Deepgram, optional)",
                type=["mp3", "wav", "m4a"],
                accept_multiple_files=True,
                help="Default: transcription OFF (no 1GB download). Set WHISPER_BACKEND to enable.",
            )
            floorplan_file = st.file_uploader("Floorplan export (JSON/CSV of rooms)", type=["json", "csv"])
            matterport = st.text_input(
                "Matterport model URL (optional)", placeholder="https://my.matterport.com/..."
            )

        section("7", "Brokerage Transactions", "Optional CSV for brokerage ROI.")
        txns_csv = st.file_uploader(
            "Closed-deal records",
            type=["csv"],
            help="Columns: agent,zip_code,date,credits_negotiated,items_requested,items_granted,deal_value",
        )

        section("8", "Sold Comps for ARV", "Optional — paste comps or connect Attom/RentCast.")
        st.caption(
            "Paste rows as: price | sqft | distance_mi | recency_days | dom — or connect Attom/RentCast keys in .env"
        )
        comps_txt = st.text_area(
            "One comp per line", height=70, placeholder="525000 | 1650 | 0.3 | 22 | 14", key="comps_txt"
        )

        run = st.form_submit_button("▶ Run Analysis", type="primary", use_container_width=True)

    if run:
        zchk = validate_zip9(zip9)
        if not (addr and city and state):
            st.error("Address, city, and state are required.")
            st.stop()
        if not zchk["valid"]:
            st.error(f"ZIP is not verification-grade: {zchk['note']}")
            st.stop()
        if not pdfs and not audios and not quotes_txt.strip():
            st.warning(
                "No inspection report, audio, or manual findings provided. "
                "You can still proceed, but results will be empty."
            )
        if not any([pdfs, audios]):
            st.warning("TIP: Upload an inspection PDF or audio recording to populate findings.")

        meta = {
            "address": addr,
            "city": city,
            "state": state,
            "zip9": zip9,
            "apn": apn,
            "property_type": ptype,
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
            "year_built": year_built,
        }
        mls = {
            "list_price": list_price or None,
            "price_per_sqft": price_psf or None,
            "dom_days": dom or None,
            "last_sale_price": last_sale or None,
            "zone": mls_zone,
            "source": mls_source,
        }
        uw = {
            "annual_premium": premium or None,
            "arv": arv or None,
            "interest_rate": interest_rate / 100,
            "monthly_rent": monthly_rent or None,
            "holding_months": holding_months,
        }
        quotes = _parse_rows(quotes_txt, ["finding_key", "contractor", "license", "low", "high", "eta_days"])
        permits = _parse_rows(
            permits_txt, ["permit_type", "permit_number", "permit_date", "status", "description"]
        )
        transactions = _parse_csv(txns_csv) if txns_csv else None
        comps_raw = _parse_rows(comps_txt, ["price", "sqft", "distance_mi", "recency_days", "dom"])
        comps = []
        for c in comps_raw:
            try:
                comps.append(
                    {
                        "price": float(str(c.get("price", 0)).replace(",", "")),
                        "sqft": float(str(c.get("sqft", 0)).replace(",", "")),
                        "distance_mi": float(c.get("distance_mi", 1) or 1),
                        "recency_days": float(c.get("recency_days", 90) or 90),
                        "dom": float(c.get("dom", 30) or 30),
                        "source": "user",
                    }
                )
            except (TypeError, ValueError):
                continue

        if not GLOBAL_LIMITER.allow("run"):
            st.error("Rate limit — please wait a minute and retry.")
            st.stop()

        with st.spinner("Fetching live government data and running analysis…"):
            try:
                session = compile_session_input(
                    meta, mls, uw, quotes, permits, pdfs, audios, floorplan_file, matterport
                )
                session["transactions"] = transactions
                session["photos"] = [{"name": p.name} for p in (photos or [])]
                session["comps"] = comps
                # Vault raw PII (TTL), keep redacted display in session log
                try:
                    vault_store(f"sess-{zip9}-{datetime.now().timestamp()}", {"address": addr, "apn": apn})
                except Exception:
                    pass
                results = run_pipeline(session)
                try:
                    from engines.db_supabase import save_estimate

                    results["persisted"] = save_estimate(
                        "streamlit-ui",
                        {
                            "zip": zip9,
                            "state": state,
                            "totals": results["cost_matrix"].get("summary", {}),
                            "findings": session.get("findings", []),
                        },
                    )
                except Exception:
                    pass
                st.session_state["session"] = session
                st.session_state["results"] = results
                st.session_state["page"] = "Analysis"
                st.rerun()
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                st.code(traceback.format_exc(), language="python")


def _parse_rows(text, cols):
    rows = []
    if not text:
        return rows
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        rows.append({cols[i]: parts[i] if i < len(parts) else "" for i in range(len(cols))})
    return rows


def _parse_csv(file):
    try:
        import io

        return pd.read_csv(io.BytesIO(file.getvalue())).to_dict("records")
    except Exception as e:
        st.warning(f"Transaction CSV could not be parsed: {e}")
        return None


# ------------------------------------------------------------------
# Page 3 - Results
# ------------------------------------------------------------------
def page_results():
    res = st.session_state["results"]
    sess = st.session_state["session"]
    st.caption(
        f"Generated {res['generated_at']} · ZIP {sess['property_data']['zip_code']} · "
        f"{len(sess['findings'])} findings · Sources: {len(sess['ingestion_report']['report_sources'])} PDF(s), "
        f"{len(sess['ingestion_report']['audio_sources'])} audio"
    )

    # Lender share link (full-width, copy-friendly) + export row
    with st.container(border=True):
        st.markdown(
            "**Lender share link** <span class='pill-muted'>expiring · redacted PII</span>",
            unsafe_allow_html=True,
        )
        tok = res.get("share_token")
        if tok:
            from engines.share_engine import share_url as _su

            st.code(_su(tok), language="text")
        else:
            st.caption("Share link unavailable for this run.")
    d1, d2, d3 = st.columns(3)
    with d1:
        try:
            from engines.export_pdf import build_pdf_package as _pdf

            pdf_bytes = _pdf(res["cost_matrix"].get("summary", {}), res["cost_matrix"].get("line_items", []))
            st.download_button(
                "Full PDF package",
                pdf_bytes,
                file_name="lender_repair_package.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.caption(f"PDF unavailable: {e}")
    with d2:
        try:
            from engines.export_excel import build_excel_workbook as _xl

            xl = _xl(
                res["cost_matrix"].get("line_items", []),
                res.get("rooms") if isinstance(res.get("rooms"), list) else None,
                res.get("arv_comps") if isinstance(res.get("arv_comps"), dict) else None,
            )
            st.download_button(
                "Excel workbook",
                xl,
                file_name="repair_workbook.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.caption(f"Excel unavailable: {e}")
    with d3:
        st.download_button(
            "JSON (auditable)",
            json.dumps(res["cost_matrix"], indent=2, default=str),
            file_name="cost_matrix.json",
            use_container_width=True,
        )

    t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs(
        [
            "Financial Matrix",
            "Rooms & ARV",
            "24-Month CapEx",
            "Sandbox + Copilot",
            "Legal Addendums",
            "Market Baseline",
            "Spatial & Vision",
            "Insurance, Climate & Recalls",
            "Pages & ROI",
        ]
    )

    with t1:
        render_financial_matrix(res, sess)
    with t2:
        render_rooms_arv(res, sess)
    with t3:
        render_capex(res)
    with t4:
        render_sandbox(res)
        render_copilot(res)
    with t5:
        render_legal(res, sess)
    with t6:
        render_contractor(res, sess)
    with t7:
        render_spatial(res)
        render_vision_v2(res)
    with t8:
        render_insurance_recalls(res)
        render_climate_v2(res)
    with t9:
        render_seo_brokerage(res, sess)


def render_financial_matrix(res, sess):
    cm = res["cost_matrix"]
    s = cm["summary"]
    st.subheader("Financial Repair Matrix")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total (avg)", money(s["total_avg"]), help=f"Wage source: {s['wage_provenance']}")
    c2.metric("Total (low)", money(s["total_low"]))
    c3.metric("Total (high)", money(s["total_high"]))
    c4.metric("Items", s["total_items"])
    st.caption(f"Labor: **{s['wage_provenance']}** · Materials: **{s['ppi_provenance']}** (BLS PPI index)")

    rows = []
    for item in cm["line_items"]:
        rows.append(
            {
                "System": item["system"],
                "Severity": item["severity"],
                "Finding": item["finding"],
                "DIY": money(item["diy_low"]) + "–" + money(item["diy_high"]),
                "Contractor": money(item["contractor_low"]) + "–" + money(item["contractor_high"]),
                "Emergency": money(item["emergency_low"]) + "–" + money(item["emergency_high"]),
                "Source": badge(item["provenance"]),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    sev = s["by_severity"]
    sev_df = pd.DataFrame({"Severity": list(sev.keys()), "Est. total ($)": [int(v) for v in sev.values()]})
    fig = go.Figure(
        go.Bar(
            x=sev_df["Severity"],
            y=sev_df["Est. total ($)"],
            marker_color=["#DC2626", "#EA580C", "#CA8A04", "#16A34A"],
        )
    )
    fig.update_layout(title="Repair cost by severity", height=320, margin=dict(l=10, r=10, t=40, b=10))
    theme_plotly(fig)
    st.plotly_chart(fig, use_container_width=True)


def render_capex(res):
    capex = res["capex"]
    st.subheader("24-Month CapEx Replacement Timeline")
    s = capex["summary"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Replacement value", money(s["total_replacement_value"]))
    c2.metric("Immediate", money(s["immediate_cost"]))
    c3.metric("12-mo", money(s["12mo_cost"]))
    c4.metric("24-mo", money(s["24mo_cost"]))
    st.caption(f"Weighted 24-mo risk exposure: {money(s['weighted_risk_exposure'])}")

    if capex["visual_timeline"]:
        months = [v["month"] for v in capex["visual_timeline"]]
        costs = [v["total_cost"] for v in capex["visual_timeline"]]
        fig = go.Figure(go.Bar(x=[f"M{m}" for m in months], y=costs, marker_color="#7C3AED"))
        fig.update_layout(
            title="Projected replacement cost by month", height=320, margin=dict(l=10, r=10, t=40, b=10)
        )
        theme_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)

    rows = []
    for it in capex["timeline_items"]:
        rows.append(
            {
                "System": it["system"],
                "Severity": it["severity"],
                "Finding": it["finding"],
                "Asset age": it["current_age"],
                "Remaining life": it["remaining_life_years"],
                "Replace cost": money(it["replacement_cost"]),
                "Failure prob (24mo)": f"{it['failure_probability_24mo']}%",
                "Projected": it["projected_failure_date"],
                "Urgency": it["urgency_category"],
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_sandbox(res):
    sandbox = res["sandbox"]
    st.subheader("Sellers-Credit Negotiation Sandbox")
    items = sandbox["items"]
    df = pd.DataFrame(
        [
            {
                "id": i,
                "Include": i.get("selected", False),
                "System": i.get("system", ""),
                "Severity": i.get("severity", ""),
                "Description": i.get("description", ""),
                "Credit (avg)": money(i.get("estimated_cost", 0)),
                "Low": money(i.get("estimated_low", 0)),
                "High": money(i.get("estimated_high", 0)),
                "Repair type": i.get("repair_type", "seller_credit"),
            }
            for i in items
        ]
    )
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        disabled=["System", "Severity", "Description", "Credit (avg)", "Low", "High"],
        key="sandbox_editor",
    )
    selected_ids = set(edited[edited["Include"]].index.tolist())
    sel_items = [items[i] for i in selected_ids if 0 <= i < len(items)]

    for it in sel_items:
        it["selected"] = True
    for i, it in enumerate(items):
        it["selected"] = i in selected_ids

    totals = calculate_sandbox_totals(items, {"leverage_score": res["leverage"]})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Requested", money(totals["total_requested"]))
    c2.metric("Range", f"{money(totals['total_low_range'])}–{money(totals['total_high_range'])}")
    c3.metric(
        "Expected concession",
        money(totals["expected_concession"]),
        help=f"Based on market leverage {res['leverage']}/100",
    )
    c4.metric("Selected items", totals["selected_items"])

    st.subheader("Negotiation strategies")
    for strat in res["strategies"]:
        st.markdown(f"- **{strat['title']}** — {strat['detail']}  `{strat['relevance']}`")

    scenarios = [
        {"name": "Full credit request", "description": "All critical/high items", "changes": []},
        {"name": "Repair-or-credit", "description": "Convert top 3 to seller repair", "changes": []},
    ]
    cmp = generate_scenario_comparison(items, scenarios, {"leverage_score": res["leverage"]})
    for sc in cmp:
        st.markdown(
            f"**{sc['scenario_name']}:** request {money(sc['totals']['total_requested'])} "
            f"→ expected concession {money(sc['totals']['expected_concession'])}"
        )


def render_legal(res, sess):
    legal = res["legal"]
    st.subheader("Legal Addendums")
    st.markdown(f"**{legal['addendum_type']}** · {legal['address']} · {legal['date']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Seller repairs", legal["total_repair_items"])
    c2.metric("Seller credits", legal["total_credit_items"])
    c3.metric("Total requested", money(legal["total_requested_value"]))
    st.text_area("Repair Request Addendum", legal["addendum_text"], height=320)

    high_risk = [f for f in sess["findings"] if f.get("severity") in ("CRITICAL", "HIGH")]
    if high_risk:
        escrow = generate_escrow_holdback_agreement(sess["property_data"], high_risk, res["bids"])
        st.text_area("Escrow Holdback Agreement (preview)", str(escrow), height=260)
    st.download_button("Download addendum (.txt)", legal["addendum_text"], file_name="repair_addendum.txt")


def render_contractor(res, sess):
    st.subheader("Contractor Dispatch & Market Baseline")
    st.caption(
        "Deterministic **market-baseline estimates** (not simulations): **USER-provided quotes** "
        "(authoritative) or **real BLS OEWS wage baselines** + standard margin. No invented firms, ever."
    )
    bids = res["bids"]
    rows = []
    for b in bids.values():
        rows.append(
            {
                "System": b["system"],
                "Severity": b["severity"],
                "Trade": b["trade"],
                "Finding": b["finding"],
                "Contractor": b["contractor"],
                "License": b["license_no"],
                "Bid low": money(b["bid_low"]),
                "Bid high": money(b["bid_high"]),
                "ETA days": b["eta_days"],
                "Source": badge(b["cost_source"]),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Priority dispatch queue")
    for r in get_contractor_recommendations(bids, 5):
        st.markdown(
            f"- **{r['severity']} {r['system']}**: {r['contractor']} — "
            f"{money(r['bid_low'])}–{money(r['bid_high'])}  `{r['cost_source']}`"
        )

    st.caption("Add real quotes on Page 1 → Section 4 to replace baselines.")


def render_spatial(res):
    sp = res["spatial"]
    st.subheader("Spatial 3D Flaw Mapping")
    st.caption(sp["floor_plan_note"])
    if sp["floor_plan"]:
        rooms = sp["floor_plan"]
        fig = go.Figure()
        for room in rooms:
            x, y = float(room.get("x", 5)), float(room.get("y", 5))
            w, h = float(room.get("width", 3)), float(room.get("height", 2))
            fig.add_shape(
                type="rect",
                x0=x - w / 2,
                y0=y - h / 2,
                x1=x + w / 2,
                y1=y + h / 2,
                line=dict(color="#888", width=1),
                fillcolor="rgba(200,200,200,0.25)",
            )
            fig.add_annotation(
                x=x, y=y + h / 2 + 0.2, text=room.get("name", ""), showarrow=False, font=dict(size=10)
            )
        for m in sp["findings_mapped"]:
            fig.add_trace(
                go.Scatter(
                    x=[m["x_position"]],
                    y=[m["y_position"]],
                    mode="markers+text",
                    marker=dict(size=14, color=m["color"]),
                    text=[f"{m['system']}"],
                    textposition="top center",
                    name=f"{m['severity']} {m['system']}",
                    hovertemplate=f"{m['finding']}<br>{m['severity']} · {m['system']}<extra></extra>",
                )
            )
        fig.update_layout(
            height=560,
            margin=dict(l=10, r=10, t=40, b=10),
            title=f"Floor plan ({sp['floor_plan_provenance']})",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        theme_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)
    st.caption("Upload a floorplan JSON/CSV or Matterport model on Page 1 for true spatial placement.")


def render_rooms_arv(res, sess):
    st.subheader("Room-by-room condition · Low / Mid / High · Priority")
    st.caption(
        "Good / Fair / Poor / Gut per room, mapped to state BLS labor. "
        "Immediate (<30d) / 6-mo / 12-mo / Deferred — the format AI answers quote."
    )
    rooms = res.get("rooms")
    if isinstance(rooms, list) and rooms:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Room": r.get("room"),
                        "Condition": r.get("condition"),
                        "Priority": r.get("priority"),
                        "Items": r.get("items"),
                        "Worst": r.get("worst_severity"),
                        "Low": money(r.get("low")),
                        "Mid": money(r.get("mid")),
                        "High": money(r.get("high")),
                        "Top issue": str(r.get("top_issue", ""))[:100],
                    }
                    for r in rooms
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No room-mapped findings. Add location text (e.g. 'in kitchen') to findings.")
    st.subheader("Comp-backed ARV + rents")
    arv = res.get("arv_comps") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("ARV low", money(arv.get("arv_low")))
    c2.metric("ARV mid", money(arv.get("arv_mid")))
    c3.metric("ARV high", money(arv.get("arv_high")))
    st.caption(f"Provenance: **{arv.get('provenance', 'UNAVAILABLE')}** — {arv.get('explain', '')}")
    if isinstance(arv.get("comps_weighted"), list) and arv["comps_weighted"]:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Price": money(c.get("price")),
                        "$/sqft": c.get("ppsf"),
                        "Dist mi": c.get("distance_mi"),
                        "Recency d": c.get("recency_days"),
                        "DOM": c.get("dom"),
                        "Weight": f"{(c.get('weight_norm', 0) or 0) * 100:.0f}%",
                    }
                    for c in arv["comps_weighted"]
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning(
            "No comps supplied — ARV is list-price fallback (MODELED). Paste sold comps on Inputs → §8 "
            "or set ATTOM_API_KEY / RENTCAST_API_KEY for live enrichment."
        )
    inv = res.get("investor", {})
    if isinstance(inv, dict) and inv.get("max_offer"):
        st.markdown(
            f"**MAO math:** {money(inv.get('max_offer'))} = {money(inv.get('arv'))} − "
            f"{money(inv.get('repair'))} (repair) − {money(inv.get('holding'))} (holding) − "
            f"{money(inv.get('closing'))} (closing) − {money(inv.get('profit_target'))} (target)"
        )


def render_copilot(res):
    st.subheader("Agentic negotiation copilot")
    cop = res.get("offer_copilot") or {}
    if cop.get("letter"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Total ask", money(cop.get("total_ask")))
        c2.metric("Expected concession", money(cop.get("expected_concession")))
        c3.metric("Leverage", f"{cop.get('leverage')}/100")
        st.text_area("Offer credit language (paste into addendum)", cop["letter"], height=260)
        st.caption("Citations: " + " · ".join(cop.get("citations", [])[:8]))
        st.download_button(
            "Download copilot letter (.txt)", cop["letter"], file_name="offer_credit_letter.txt"
        )
    else:
        st.caption("Copilot unavailable for this run.")


def render_vision_v2(res):
    st.subheader("Vision 2.0 — photo → finding")
    v = res.get("vision_v2") or {}
    photos = v.get("photos") or []
    if photos:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Photo": p.get("photo"),
                        "Condition": p.get("condition"),
                        "System": p.get("system"),
                        "Severity hint": p.get("severity_hint"),
                        "Confidence": p.get("confidence"),
                        "BBox": str(p.get("bbox") or "pending geometry"),
                        "Provenance": p.get("provenance"),
                    }
                    for p in photos
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        with st.expander("What we could NOT see (honest limits)"):
            for n in v.get("not_visible_global", []):
                st.markdown(f"- {n}")
    else:
        st.caption(
            "No photos uploaded. Vision 2.0 maps filenames/captions deterministically; "
            "add YOLOv8-seg locally or a multimodal key for bounding boxes."
        )


def render_climate_v2(res):
    st.subheader("Climate + insurance v2 (2026 FL/CA headlines)")
    c = res.get("climate_v2") or {}
    if c.get("premium_impact") is not None:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Wildfire", c.get("wildfire_score"))
        c2.metric("Hurricane", c.get("hurricane_score"))
        c3.metric("Premium impact", money(c.get("premium_impact")))
        c4.metric("Non-renewal", c.get("non_renewal_risk"))
        st.info(c.get("headline", ""))
        for m in c.get("mitigations", []):
            st.markdown(f"- {m}")
        st.caption(f"Sources: {', '.join(c.get('sources', []))} · Provenance {c.get('provenance')}")
    else:
        st.caption("Climate v2 unavailable.")


def render_insurance_recalls(res):
    ins = res["insurance_scorecard"]
    st.subheader("Insurance Risk Scorecard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Insurability", f"{ins['insurability_score']}/100", ins["grade"])
    c2.metric("Red flags", ins["red_flags"])
    c3.metric("Max denial prob.", f"{ins['max_denial_prob']}%")
    c4.metric("Annual premium impact", money(ins["annual_impact"]))
    st.info(f"Premium basis: **{ins['premium_provenance']}** — {ins['verdict']}")
    for r in ins["recommendations"]:
        st.markdown(f"- {r}")

    recalls = res["recalls"]
    st.subheader("Product Recall Alerts (live CPSC)")
    st.caption(f"Source: {recalls['summary']['source']} · Status: {recalls['summary']['api_status']}")
    if recalls["recall_results"]:
        rows = []
        for r in recalls["recall_results"]:
            rows.append(
                {
                    "Finding": r["finding_description"],
                    "Product": ", ".join(r["product_names"]),
                    "Manufacturer": ", ".join(r["manufacturers"]),
                    "Hazard": ", ".join(r["hazard_types"]),
                    "Date": r["recall_date"],
                    "Remedy": r["remedy"][:80],
                    "Action": r["action_required"][:100],
                    "URL": r["recall_url"],
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.metric("Potential avoided cost (heuristic)", money(recalls["summary"]["total_potential_savings"]))
    else:
        st.write("No CPSC recall matches from the findings. (Real query, honest result.)")


def render_seo_brokerage(res, sess):
    seo = res["seo"]
    st.subheader("Programmatic Local Landing Pages")
    st.caption(f"{seo['total_pages']} pages generated · Analytics: {seo['analytics_status']}")
    rows = []
    for p in seo["pages"]:
        rows.append(
            {
                "System": p["system_type"],
                "Slug": f"/{p['page_slug']}",
                "Avg cost": money(p["avg_cost"]) if p["avg_cost"] else "—",
                "Cost status": badge(p["cost_provenance"]),
                "H1": p["h1"],
                "Meta": p["meta_description"][:90],
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    for p in seo["pages"][:2]:
        with st.expander(p["h1"]):
            for sec in p["content_sections"]:
                st.markdown(f"**{sec['heading']}**\n\n{sec['content']}")

    st.subheader("Brokerage ROI")
    br = res["brokerage"]
    if br.get("status") == "VERIFIED":
        s = br["summary"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Deals", s["total_transactions"])
        c2.metric("Credits negotiated", money(s["total_credits_negotiated"]))
        c3.metric("Success rate", f"{s['overall_success_rate']}%")
        st.dataframe(pd.DataFrame(br["agent_performance"]), use_container_width=True, hide_index=True)
        for i in br["insights"]:
            st.markdown(f"- {i}")
    else:
        st.warning(br.get("note", "No transaction data."))
        with st.expander("How to import"):
            st.code(
                "agent,zip_code,date,credits_negotiated,items_requested,items_granted,deal_value\n"
                "Jane Doe,90210,2026-03-01,12500,6,5,950000"
            )


def page_analysis():
    """Page 2 · Deep Analysis & Research — long-form dossier across all 21 modules."""
    res = st.session_state["results"]
    sess = st.session_state["session"]
    d = res["deep_analysis"]

    st.caption(
        "Long-form, line-item analytical output across all 21 platform modules. "
        "Every figure is real (live government data, user MLS/quotes) or honestly "
        "labeled MODELED/UNAVAILABLE. Nothing is fabricated."
    )

    # ---- Executive summary strip ----
    cm = res["cost_matrix"]["summary"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Findings analyzed", len(sess["findings"]))
    c2.metric("Total repair (avg)", money(cm["total_avg"]))
    c3.metric("Total repair (range)", f"{money(cm['total_low'])}–{money(cm['total_high'])}")
    c4.metric("Market anchor", d["module_04_market"]["anchor"])
    c5.metric("Insurability score", f"{d['module_15_insurance']['score']}/100")

    # ---- Master matrix ----
    st.subheader("📋 Comprehensive Deep-Dive Output Matrix")
    st.caption(
        "System / Issue / Severity / Immediate Repair Range / Future Risk Horizon / "
        "Strategic Action / Permit / Photos / Recalls / Bid — merged per finding."
    )
    st.dataframe(pd.DataFrame(d["matrix"]), use_container_width=True, hide_index=True)

    # ---- Per-finding deep dive ----
    st.subheader("🔎 Per-Finding Deep Dive")
    for f in d["deep_findings"]:
        with st.expander(
            f"#{f['index']} [{f['severity']}] {f['system']} — {f['description'][:80]}",
            expanded=f["severity"] in ("CRITICAL", "HIGH"),
        ):
            st.markdown(f"**{f['description']}**")
            st.caption(
                f"Location: {f['location']} · Source: {f['source_type']} "
                f"{f['source_file']} · Photos matched: {len(f['photos'])}"
            )
            col1, col2, col3, col4 = st.columns(4)
            cost = f["cost"] or {}
            col1.metric("Repair range", f"{money(cost.get('total_low'))}–{money(cost.get('total_high'))}")
            col1.caption(f"DIY: {money(cost.get('diy_low'))}–{money(cost.get('diy_high'))}")
            cap = f["capex"] or {}
            col2.metric("24-mo failure prob", f"{cap.get('failure_probability_24mo', '—')}%")
            col2.caption(
                f"Replace: {money(cap.get('replacement_cost'))} · proj. {cap.get('projected_failure_date', '—')}"
            )
            col3.metric(
                "Bid", f"{money(f['bid']['bid_low'])}–{money(f['bid']['bid_high'])}" if f["bid"] else "—"
            )
            col3.caption(f["bid"]["cost_source"] if f["bid"] else "Awaiting quote")
            col4.metric("Recalls", len(f["recalls"]))
            col4.metric(
                "Permit",
                (f["permit_xref"] or {}).get("permit_status", "—"),
                help=((f["permit_xref"] or {}).get("recommendation", "")),
            )

    # ---- Module sections ----
    modules = [
        _render_m01,
        _render_m02,
        _render_m03,
        _render_m04,
        _render_m05,
        _render_m06,
        _render_m07,
        _render_m08,
        _render_m09,
        _render_m10,
        _render_m11,
        _render_m12,
        _render_m13,
        _render_m14,
        _render_m15,
        _render_m16,
        _render_m17,
        _render_m18,
        _render_m19,
        _render_m20,
        _render_m21,
    ]
    for fn in modules:
        fn(d, res, sess)


def _module_header(m, icon):
    st.divider()
    st.subheader(f"{icon} {m['title']}")
    st.markdown(f"Status: {badge(m['status'])}")
    st.markdown(m["narrative"])


def _render_m01(d, res, sess):
    m = d["module_01_parse"]
    _module_header(m, "🛠️")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total findings", m["stats"]["total_findings"])
    c2.metric("From PDF", m["stats"]["from_pdf"])
    c3.metric("From audio", m["stats"]["from_audio"])
    c4.metric("PDF images extracted", m["stats"]["pdf_images"])
    st.markdown("**Source files processed:**")
    for s in m["sources"]:
        st.markdown(f"- `{s['file']}` — {s['status']} ({s.get('findings', 0)} findings)")
    for s in m["audio_sources"]:
        st.markdown(f"- 🎙️ `{s['file']}` — {s['status']}")


def _render_m02(d, res, sess):
    m = d["module_02_cost"]
    _module_header(m, "🎛️")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total low", money(m["total_low"]))
    c2.metric("Total avg", money(m["total_avg"]))
    c3.metric("Total high", money(m["total_high"]))
    c4.metric("Wage source", m["wage_provenance"])
    st.caption(f"Material index: {m['ppi_provenance']}")
    rows = [
        {
            "System": i["system"],
            "Severity": i["severity"],
            "Finding": i["finding"],
            "DIY": f"{money(i['diy'][0])}–{money(i['diy'][1])}",
            "Contractor": f"{money(i['contractor'][0])}–{money(i['contractor'][1])}",
            "Emergency": f"{money(i['emergency'][0])}–{money(i['emergency'][1])}",
            "Source": badge(i["provenance"]),
        }
        for i in m["line_items"]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_m03(d, res, sess):
    m = d["module_03_depreciation"]
    _module_header(m, "📊")
    s = m["summary"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Systems assessed", s["total_systems_assessed"])
    c2.metric("Total replacement value", money(s["total_replacement_value"]))
    c3.metric("Weighted 24-mo risk", money(s["weighted_24mo_risk"]))
    rows = [
        {
            "System": i["system"],
            "Severity": i["severity"],
            "Asset type": i["asset_type"],
            "Est. age": i["estimated_age"],
            "Useful life": i["useful_life"],
            "Remaining life": i["remaining_life"],
            "Fail prob (24mo)": f"{i['failure_probability_24mo']}%",
            "Replacement": money(i["replacement_cost_avg"]),
            "Projected": i["projected_failure_year"],
            "Urgency": i["replacement_urgency"],
        }
        for i in m["capex_items"]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if m["appliance_metadata"]:
        st.markdown("**Parsed appliance metadata (model year / condition cues):**")
        st.dataframe(pd.DataFrame(m["appliance_metadata"]), use_container_width=True, hide_index=True)


def _render_m04(d, res, sess):
    m = d["module_04_market"]
    _module_header(m, "📈")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Anchor", m["anchor"])
    c2.metric("List price", money(m["list_price"]) if m["list_price"] else "—")
    c3.metric("Price/sqft", m["price_per_sqft"] if m["price_per_sqft"] else "—")
    c4.metric("DOM", m["dom_days"] if m["dom_days"] is not None else "—")
    st.markdown(f"**Position:** `{m['market_position']}` — {m['anchor_description']}")
    if m["acs"].get("median_home_value"):
        st.markdown(
            f"**Census ACS ({m['acs'].get('acs_year', '')})** zip median: "
            f"${m['acs']['median_home_value']:,.0f} · median rent "
            f"${m['acs'].get('median_gross_rent', 0):,.0f} · owner-occupied "
            f"{m['acs'].get('owner_occupied_pct', 0)}% · status {badge(m['acs'].get('status'))}"
        )
    st.markdown("**Negotiation strategies:**")
    for s in m["strategies"]:
        st.markdown(f"- **{s['title']}** — {s['detail']} `{s['relevance']}`")


def _render_m05(d, res, sess):
    m = d["module_05_export"]
    _module_header(m, "📥")
    st.markdown("Formats: " + ", ".join(f"`{f}`" for f in m["formats"]))
    st.caption("Generate the branded PDF package and interactive buyer portal from the Results page.")


def _render_m06(d, res, sess):
    m = d["module_06_vision"]
    _module_header(m, "📸")
    c1, c2, c3 = st.columns(3)
    c1.metric("Photos extracted", m["total_images"])
    c2.metric("Findings with photos", len(m["matched"]))
    c3.metric("Match rate", f"{m['match_rate']}%")
    if m["critical_with_photos"]:
        st.markdown("**Critical/high findings with photo evidence:**")
        for e in m["critical_with_photos"]:
            st.markdown(
                f"- [{e['severity']}] {e['system']} — {e['description']} ({e['photo_count']} photo(s))"
            )
    if m["findings_missing_photos"]:
        st.markdown(
            f"**{len(m['findings_missing_photos'])} findings lack photo evidence** — request "
            "original photos from the inspector for these line items."
        )


def _render_m07(d, res, sess):
    m = d["module_07_permits"]
    _module_header(m, "🗄️")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Permits on record", m["total_permits"])
    c2.metric("Closed", m["closed"])
    c3.metric("Open", m["open"])
    c4.metric("Expired", m["expired"])
    st.markdown(
        f"Overall: **{m['compliance']['overall_status']}** · Unpermitted flags: {m['unpermitted_flags']}"
    )
    rows = [
        {
            "Finding": x["finding"],
            "System": x["system"],
            "Permit status": x["permit_status"],
            "Risk": x.get("risk_level", ""),
            "Recommendation": x.get("recommendation", ""),
        }
        for x in m["cross_reference"]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if m["needs"]:
        st.markdown("**Permits likely required (from findings):**")
        st.dataframe(pd.DataFrame(m["needs"]), use_container_width=True, hide_index=True)


def _render_m08(d, res, sess):
    m = d["module_08_capex_24mo"]
    _module_header(m, "📅")
    s = m["summary"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Immediate", money(s["immediate_cost"]))
    c2.metric("12-mo", money(s["12mo_cost"]))
    c3.metric("24-mo", money(s["24mo_cost"]))
    c4.metric("Weighted risk", money(s["weighted_risk_exposure"]))
    if m["timeline"]:
        fig = go.Figure(
            go.Bar(
                x=[f"M{v['month']}" for v in m["timeline"]],
                y=[v["total_cost"] for v in m["timeline"]],
                marker_color="#7C3AED",
            )
        )
        fig.update_layout(
            title="Projected replacement cash outlay by month (24-mo horizon)",
            height=320,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        theme_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)
    rows = [
        {
            "System": i["system"],
            "Severity": i["severity"],
            "Finding": i["finding"],
            "Remaining life": i["remaining_life"],
            "Fail prob": f"{i['failure_probability_24mo']}%",
            "Replacement": money(i["replacement_cost_avg"]),
            "Projected": i["projected_failure_year"],
            "Urgency": i["replacement_urgency"],
        }
        for i in m["capex_items"]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_m09(d, res, sess):
    m = d["module_09_sandbox"]
    _module_header(m, "🤝")
    sb = res["sandbox"]
    df = pd.DataFrame(
        [
            {
                "System": i["system"],
                "Severity": i["severity"],
                "Description": i["description"],
                "Est. cost": money(i["estimated_cost"]),
                "Type": i["repair_type"],
            }
            for i in sb["items"]
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown(f"**Market leverage:** {m['leverage']}/100 — model scenarios live on the Results page.")


def _render_m10(d, res, sess):
    m = d["module_10_dispatch"]
    _module_header(m, "🧰")
    rows = [
        {
            "System": b["system"],
            "Severity": b["severity"],
            "Trade": b["trade"],
            "Finding": b["finding"],
            "Contractor": b["contractor"],
            "License": b["license_no"],
            "Bid": f"{money(b['bid_low'])}–{money(b['bid_high'])}",
            "ETA days": b["eta_days"],
            "Source": badge(b["cost_source"]),
        }
        for b in m["bids"]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("Enter real quotes on Page 1 → Section 4 to replace BLS baselines with binding bids.")


def _render_m11(d, res, sess):
    m = d["module_11_legal"]
    _module_header(m, "⚖️")
    c1, c2, c3 = st.columns(3)
    c1.metric("Seller repairs", len(m["seller_repairs"]))
    c2.metric("Seller credits", len(m["seller_credits"]))
    c3.metric("Total requested", money(m["total_requested"]))
    st.markdown(f"**{m['addendum_type']}**")
    st.text_area("Addendum text", m["addendum_text"], height=240)
    st.download_button("Download addendum (.txt)", m["addendum_text"], file_name="repair_addendum.txt")


def _render_m12(d, res, sess):
    m = d["module_12_environmental"]
    _module_header(m, "🌍")
    g = m["geocoding"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Address resolution", g["status"])
    c1.caption(f"{g.get('matched_address', '')} · {g.get('county', '')}")
    c2.metric("Flood zone", m["flood"].get("risk_level", "—"), help=m["flood"].get("status"))
    c3.metric(
        "Seismic",
        m["seismic"].get("risk_level", "—"),
        help=f"sds={m['seismic'].get('sds')} · {m['seismic'].get('status')}",
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Quakes 75km/1yr", m["earthquakes"].get("count_75km_1yr", 0))
    c1.caption(f"Largest: {m['earthquakes'].get('largest_magnitude')} · {m['earthquakes'].get('status')}")
    c2.metric("Weather", m["weather"].get("conditions", "—"), help=f"{m['weather'].get('temperature_f')}°F")
    c3.metric("Overall risk", m["summary_level"])
    st.markdown(
        f"Finding-derived risks: moisture={m['finding_risks']['mold_moisture']}, "
        f"foundation={m['finding_risks']['foundation']}, fire={m['finding_risks']['fire']}, "
        f"electrical={m['finding_risks']['electrical']}"
    )


def _render_m13(d, res, sess):
    m = d["module_13_brokerage"]
    _module_header(m, "🏢")
    if m["status"] == "VERIFIED":
        s = m["summary"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Deals", s["total_transactions"])
        c2.metric("Credits negotiated", money(s["total_credits_negotiated"]))
        c3.metric("Success rate", f"{s['overall_success_rate']}%")
        c4.metric("Deal value", money(s["total_deal_value"]))
        st.dataframe(pd.DataFrame(m["agents"]), use_container_width=True, hide_index=True)
        for i in m["insights"]:
            st.markdown(f"- {i}")
    else:
        st.warning(m.get("note", "Import transaction CSV on Page 1 to unlock."))


def _render_m14(d, res, sess):
    m = d["module_14_leadmagnet"]
    _module_header(m, "📢")
    st.markdown(f"Widget: **{m['widget']['title']}** · CTA: _{m['widget']['cta']}_")
    st.markdown(f"Capture fields: {', '.join(m['widget']['capture'])} — deep report gated behind capture.")
    st.markdown(f"Analytics: `{m['analytics_status']}` — {m['analytics_note']}")
    for p in m["pages"][:3]:
        st.markdown(f"- `/{p['page_slug']}` — {p['h1']}")


def _render_m15(d, res, sess):
    m = d["module_15_insurance"]
    _module_header(m, "🛡️")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Insurability", f"{m['score']}/100", m["grade"])
    c2.metric("Red flags", len(m["red_flags"]))
    c3.metric("Max denial prob", f"{m['max_denial']}%")
    c4.metric("Annual premium impact", money(m["annual_impact"]))
    st.markdown(f"Premium basis: **{m['premium_provenance']}** — {m['verdict']}")
    for r in m["red_flags"]:
        st.markdown(
            f"- **{r['red_flag_type']}** (score {r['risk_score']}, denial {r['denial_probability'] * 100:.0f}%): "
            f"{r['description']} — {r['recommendation']}"
        )


def _render_m16(d, res, sess):
    m = d["module_16_investor"]
    _module_header(m, "📐")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("List price", money(m["listing_price"]), help=m["list_provenance"])
    c2.metric("ARV", money(m["arv"]), help=m["arv_provenance"])
    c3.metric("Max allowable offer", money(m["max_offer"]))
    c4.metric("Profit target", money(m["profit_target"]))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cap rate", f"{m['cap_rate']}%")
    c2.metric("Cash-on-cash", f"{m['coc']}%")
    c3.metric("Monthly rent", money(m["rental"]), help=m["rent_provenance"])
    c4.metric("5-yr CapEx forecast", money(sum(y["total_expected_cost"] for y in m["forecast"])))
    st.markdown(
        "**MAO math:** "
        + money(m["max_offer"])
        + " = "
        + money(m["arv"])
        + " − "
        + money(m["repair"])
        + " (repair) − "
        + money(m["holding"])
        + " (holding) − "
        + money(m["closing"])
        + " (closing) − "
        + money(m["profit_target"])
        + " (target)"
    )
    for a in m["analysis"]:
        st.markdown(f"- {a}")
    rows = [
        {
            "Year": y["year"],
            "Expected cost": money(y["total_expected_cost"]),
            "Items at risk": y["items_at_risk"],
        }
        for y in m["forecast"]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_m17(d, res, sess):
    m = d["module_17_escrow"]
    _module_header(m, "🏦")
    if m["items"]:
        c1, c2 = st.columns(2)
        c1.metric("Total holdback", money(m["total_holdback"]))
        c2.metric("Multiplier", f"{m['multiplier']}x (standard 1.5x–2x)")
        rows = [
            {
                "Finding": i["finding"],
                "System": i["system"],
                "Severity": i["severity"],
                "Contractor bid": money(i["contractor_bid"]),
                "Holdback (1.5x)": money(i["holdback_amount"]),
                "Release conditions": i["release_conditions"],
                "Milestone 1": f"{i['milestone_1_pct']}% — {i['milestone_1']}",
                "Milestone 2": f"{i['milestone_2_pct']}% — {i['milestone_2']}",
            }
            for i in m["items"]
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.write("No critical/high findings to hold back.")


def _render_m18(d, res, sess):
    m = d["module_18_seo"]
    _module_header(m, "🌐")
    c1, c2 = st.columns(2)
    c1.metric("Pages generated", m["total_pages"])
    c2.metric("Analytics", m["analytics_status"])
    rows = [
        {
            "System": p["system_type"],
            "Slug": f"/{p['page_slug']}",
            "Avg cost": money(p["avg_cost"]) if p["avg_cost"] else "—",
            "Cost status": badge(p["cost_provenance"]),
        }
        for p in m["pages"]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_m19(d, res, sess):
    m = d["module_19_audio"]
    _module_header(m, "🎙️")
    c1 = st.columns(1)[0]
    c1.metric("Findings from audio", m["from_audio"])
    for s in m["sources"]:
        st.markdown(f"- 🎙️ `{s['file']}` — {s['status']}")
    if not m["from_audio"]:
        st.info(
            "No audio recorded. Record inspector walk-through notes on Page 1 → Section 6 "
            "and they will be transcribed by the local Whisper model."
        )


def _render_m20(d, res, sess):
    m = d["module_20_recalls"]
    _module_header(m, "📦")
    c1, c2 = st.columns(2)
    c1.metric("Recall matches", m["total"])
    c2.metric("Potential avoided cost (heuristic)", money(m["savings"]))
    if m["results"]:
        rows = [
            {
                "Finding": r["finding_description"],
                "Product": ", ".join(r["product_names"]),
                "Manufacturer": ", ".join(r["manufacturers"]),
                "Hazard": ", ".join(r["hazard_types"]),
                "Remedy": r["remedy"][:90],
                "Action": r["action_required"][:100],
                "URL": r["recall_url"],
            }
            for r in m["results"]
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.write("No CPSC recall matches from the findings. (Real query, honest result.)")


def _render_m21(d, res, sess):
    m = d["module_21_spatial"]
    _module_header(m, "📐")
    st.caption(m["note"])
    if m["floor_plan"]:
        fig = go.Figure()
        for room in m["floor_plan"]:
            x, y = float(room.get("x", 5)), float(room.get("y", 5))
            w, h = float(room.get("width", 3)), float(room.get("height", 2))
            fig.add_shape(
                type="rect",
                x0=x - w / 2,
                y0=y - h / 2,
                x1=x + w / 2,
                y1=y + h / 2,
                line=dict(color="#888", width=1),
                fillcolor="rgba(200,200,200,0.25)",
            )
            fig.add_annotation(
                x=x, y=y + h / 2 + 0.2, text=room.get("name", ""), showarrow=False, font=dict(size=10)
            )
        for mk in m["findings_mapped"]:
            fig.add_trace(
                go.Scatter(
                    x=[mk["x_position"]],
                    y=[mk["y_position"]],
                    mode="markers+text",
                    marker=dict(size=14, color=mk["color"]),
                    text=[f"{mk['system']}"],
                    textposition="top center",
                    name=f"{mk['severity']} {mk['system']}",
                    hovertemplate=f"{mk['finding']}<br>{mk['severity']}<extra></extra>",
                )
            )
        fig.update_layout(
            height=560,
            margin=dict(l=10, r=10, t=40, b=10),
            title=f"Floor plan ({m['provenance']})",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        theme_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)


def page_health():
    st.caption(
        "Official endpoints first; proxies labeled fallback. Retries + backoff + timeouts via shared session. "
        "Honest UNAVAILABLE when unreachable — nobody else admits it. Results cached 1h."
    )
    try:
        from config import config_version

        st.caption(
            f"Config version: `{config_version()}` · Whisper backend: `{__import__('os').environ.get('WHISPER_BACKEND', 'none')}`"
        )
        det = _cached_detailed_health()
        rows = []
        for k, v in det.items():
            if k in ("latency_ms", "official_endpoints"):
                continue
            if isinstance(v, dict) and "ok" in v:
                status = (
                    "Operational"
                    if v["ok"]
                    else ("Needs API key" if v.get("status") == "REQUIRES_KEY" else "Unreachable")
                )
                rows.append(
                    {
                        "Source": k.replace("_", " ").title(),
                        "Status": (
                            "🟢 " if v["ok"] else ("🟠 " if v.get("status") == "REQUIRES_KEY" else "🔴 ")
                        )
                        + status,
                        "Checked (UTC)": str(v.get("at", ""))[:19],
                    }
                )
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        lat = det.get("latency_ms") or {}
        if lat:
            section("H-1", "API latency", "In-session per-host timing from the shared HTTP client.")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Host": h,
                            "Calls": d.get("calls"),
                            "p50 ms": d.get("p50_ms"),
                            "Max ms": d.get("max_ms"),
                            "Last": d.get("last_status"),
                        }
                        for h, d in lat.items()
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        with st.expander("Official endpoints"):
            st.json(det.get("official_endpoints", {}))
    except Exception as e:
        st.warning(f"Detailed health unavailable ({e}); basic check below.")
        health = check_api_health()
        for k, v in health.items():
            ok = "🟢" if v is True else "🟠" if v == "REQUIRES_KEY" else "🔴" if v is False else "⚪"
            st.markdown(f"{ok} **{k}** — `{v}`")
    st.caption(
        "FEMA NFHL is unreachable from some networks; the engine retries multiple hosts "
        "and reports UNAVAILABLE honestly. BLS unregistered requests are limited to 25/day "
        "— set BLS_API_KEY for full access. Census ACS needs CENSUS_API_KEY (free)."
    )


# ------------------------------------------------------------------
# Navigation
# ------------------------------------------------------------------
def main():
    qp = st.query_params
    qtheme = qp.get("theme")
    if qtheme in ("dark", "light"):
        st.session_state["theme"] = qtheme

    load_css()

    current = render_top_nav()
    apply_theme()
    page_header(current)

    if current == "Inputs":
        page_inputs()
    elif current == "Analysis":
        if "results" not in st.session_state:
            st.info("No analysis yet. Enter inputs on the **Inputs** page and press **Run Analysis**.")
        else:
            page_analysis()
    elif current == "Results":
        if "results" not in st.session_state:
            st.info("No analysis yet. Enter inputs on the **Inputs** page and press **Run Analysis**.")
        else:
            page_results()
    else:
        page_health()

    render_footer()


main()
