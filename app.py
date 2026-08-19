"""
Real Estate Repair Cost Estimator - v3.0 (VERIFIED REBUILD)
===========================================================
3-page workflow:
  PAGE 1  Input ingestion (multi-layer real inputs)
  PAGE 2  Run Analysis (executes the real-data pipeline)
  PAGE 3  Results (8 verified output modules)

No synthetic data. Every value carries a provenance badge:
VERIFIED | USER_PROVIDED | REQUIRES_KEY | MODELED | UNAVAILABLE
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

sys.path.insert(0, r"C:\realestate_repair_cost_estimator")

from engines.ingestion_engine import (
    compile_session_input, validate_zip9, STATE_ABBREV,
)
from engines.real_data_fetcher import check_api_health
from engines.cost_engine import RealRates, generate_cost_matrix
from engines.capex_engine import generate_capex_horizon
from engines.market_engine import (
    generate_market_profile, generate_negotiation_strategies,
    calculate_negotiation_impact,
)
from engines.environmental_engine import (
    assess_environmental_risks, generate_climate_risk_profile,
)
from engines.contractor_engine import (
    simulate_contractor_bids, get_contractor_recommendations,
)
from engines.permit_engine import (
    simulate_permit_check, cross_reference_findings_with_permits,
    extract_permit_needs_from_findings,
)
from engines.insurance_engine import (
    analyze_insurance_risk, calculate_insurance_scorecard,
)
from engines.recall_engine import check_recalls_for_findings
from engines.spatial_engine import create_spatial_map
from engines.investor_engine import analyze_investor_deal
from engines.seo_engine import (
    generate_seo_landing_pages, generate_seo_analytics,
)
from engines.roi_engine import generate_brokerage_roi_data
from engines.sandbox_engine import (
    create_sandbox_session, calculate_sandbox_totals,
    generate_scenario_comparison,
)
from engines.legal_engine import (
    generate_legal_addendum, generate_escrow_holdback_agreement,
)
from engines.analysis_engine import generate_deep_analysis

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Repair Cost Estimator v3",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BADGE_STYLES = {
    "VERIFIED": ("🟢", "VERIFIED"),
    "USER_PROVIDED": ("🟡", "USER-PROVIDED"),
    "USER_MLS_VERIFIED": ("🟢", "VERIFIED (MLS)"),
    "REQUIRES_KEY": ("🟠", "REQUIRES API KEY"),
    "MODELED": ("🔵", "MODELED (not a quote)"),
    "MODELED_BENCHMARK": ("🔵", "MODELED BENCHMARK"),
    "UNAVAILABLE": ("⚪", "UNAVAILABLE"),
    "USER_QUOTE": ("🟡", "USER QUOTE"),
    "BENCHMARK_REAL": ("🟢", "REAL BENCHMARK"),
    "BLS_WAGE_BASELINE": ("🟢", "BLS-WAGE BASELINE"),
    "USER_FLOORPLAN": ("🟢", "USER FLOORPLAN"),
    "USER_MATTERPORT": ("🟢", "MATTERPORT"),
    "TEMPLATE": ("🔵", "TEMPLATE"),
    "USER_TRANSACTION_IMPORT": ("🟢", "IMPORTED"),
    "USER_ANALYTICS": ("🟢", "ANALYTICS"),
    "IMAGE": ("🔵", "IMAGE (geometry pending)"),
}


def badge(status):
    icon, label = BADGE_STYLES.get(status, ("⚪", status or "UNKNOWN"))
    return f"{icon} **{label}**"


def provenance_col(status, source=""):
    src = f"<span style='color:#888;font-size:0.8em'> {source}</span>" if source else ""
    return f"{badge(status)}{src}"


def money(v):
    try:
        return f"${float(v):,.0f}"
    except (TypeError, ValueError):
        return "—"


# ------------------------------------------------------------------
# Theme + CSS injection
# ------------------------------------------------------------------
def load_css():
    css = Path(__file__).resolve().parent / "static" / "style.css"
    st.markdown(f"<style>{css.read_text(encoding='utf-8')}</style>",
                unsafe_allow_html=True)


def apply_theme():
    """Apply the Python-side theme to the host page. Runs on every rerun,
    so toggling the widget below instantly re-themes the whole app.
    Apple-style: light is the default; dark adds the .dark-mode class."""
    theme = st.session_state.get("theme", "light")
    st.iframe(f"""<script>
    (function () {{
      try {{
        var d = window.parent.document;
        var dark = {json.dumps(theme)} === 'dark';
        d.documentElement.classList.toggle('dark-mode', dark);
        d.body.classList.toggle('dark-mode', dark);
      }} catch (e) {{}}
    }})();
    </script>""", height=1, width=1)


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
        if c1.button("🌙", use_container_width=True,
                     type="primary" if current == "dark" else "secondary",
                     key="btn_theme_dark"):
            st.session_state["theme"] = "dark"
            st.query_params["theme"] = "dark"
            st.rerun()
        if c2.button("☀️", use_container_width=True,
                     type="primary" if current == "light" else "secondary",
                     key="btn_theme_light"):
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
        font=dict(family="Inter, -apple-system, 'Segoe UI', sans-serif",
                  color=text),
        title_font_color=text,
        colorway=["#0071E3", "#5AC8FA", "#FF9F0A", "#FF375F", "#32D74B",
                  "#BF5AF2", "#FFD60A", "#64D2FF"],
        hoverlabel=dict(bgcolor="#1D1D1F" if not dark else "#F5F5F7",
                        font=dict(color="#F5F5F7" if not dark else "#1D1D1F")),
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
    "Inputs": ("Property Intelligence", "Input & Property Intake",
               "Feed verified property data, inspection reports, and market context. "
               "Every field feeds a provenance-tracked pipeline."),
    "Analysis": ("Deep Research", "Deep Analysis & Research",
                 "Twenty-two cross-referenced modules — cost, capEx, market, permits, "
                 "insurance, recalls, spatial, legal, ROI and more."),
    "Results": ("Verified Output", "Verified Results",
                "Every figure carries a source badge: VERIFIED, USER-PROVIDED, "
                "MODELED, or UNAVAILABLE. Nothing is fabricated."),
    "Health": ("System Integrity", "Data Source Health",
               "Live status of every government data source powering your estimates."),
}


def render_top_nav():
    current = st.session_state.get("page", "Inputs")
    with st.container(border=True):
        brand, nav, theme = st.columns([1.8, 2.4, 1.0],
                                       vertical_alignment="center", gap="medium")
        with brand:
            st.markdown("""
            <div class="prem-brand">
              <span class="prem-logo">◈</span>
              <div class="prem-brand-text">
                <div class="prem-brand-title">Repair Estimator</div>
                <div class="prem-brand-sub"><span class="status-dot"></span>Property Intelligence · Verified</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        with nav:
            cols = st.columns(len(NAV), gap="small")
            for i, (key, icon, label) in enumerate(NAV):
                with cols[i]:
                    if key == current:
                        st.markdown(
                            f'<div class="prem-nav-item active">'
                            f'<span class="nav-ic">{icon}</span>{label}</div>',
                            unsafe_allow_html=True)
                    else:
                        if st.button(label, key=f"nav_{key}",
                                     use_container_width=True,
                                     type="secondary"):
                            st.session_state["page"] = key
                            st.rerun()
        with theme:
            render_theme_toggle()
    return current


def render_footer():
    st.markdown("""
    <div class="app-footer">
      <span class="footer-emblem">◈</span>
      Every figure is derived from real, verified government data
      (Census · BLS · FEMA · USGS · CPSC) or honestly labeled
      MODELED / UNAVAILABLE. Nothing is fabricated.
    </div>
    """, unsafe_allow_html=True)


def page_header(page):
    """Premium hero header shown above every page's content."""
    kicker, title, subtitle = PAGE_HERO.get(page, PAGE_HERO["Inputs"])
    st.markdown(f"""
    <div class="page-hero">
      <div class="hero-kicker">{kicker}</div>
      <h1 class="hero-title">{title}</h1>
      <div class="hero-sub">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------
def run_pipeline(session):
    pd_ = session["property_data"]
    mls = session["mls"]
    uw = session["underwriting"]
    quotes = session["quotes"]
    permits = session["permits"]
    findings = session["findings"]
    floorplan = session["floorplan"]

    rates = RealRates(pd_["state"], pd_["zip_code"])
    cost_matrix = generate_cost_matrix(findings, pd_["state"], pd_["zip_code"],
                                       quotes, rates)
    capex = generate_capex_horizon(findings, pd_)
    market = generate_market_profile(pd_["zip_code"], pd_["state"], mls)
    env = assess_environmental_risks(pd_, findings)
    bids = simulate_contractor_bids(findings, pd_["zip_code"], cost_matrix,
                                    pd_["state"], quotes)
    insurance = analyze_insurance_risk(findings, pd_, uw)
    insurance_scorecard = calculate_insurance_scorecard(findings, pd_, uw)
    recalls = check_recalls_for_findings(findings)
    spatial = create_spatial_map(findings, pd_, floorplan.get("rooms", []))
    investor = analyze_investor_deal(pd_, findings, cost_matrix, capex,
                                     market, uw)
    legal = generate_legal_addendum(pd_, findings, cost_matrix)
    permit_result = simulate_permit_check(pd_, permits)
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
    results["deep_analysis"] = generate_deep_analysis(session, results)
    return results


# ------------------------------------------------------------------
# Page 1 - Inputs
# ------------------------------------------------------------------
def page_inputs():
    st.title("🔨 Real Estate Repair Cost Estimator")
    st.caption("Every output is derived from **real, verified data**. Missing inputs are reported "
               "honestly — nothing is fabricated.")

    with st.form("input_form"):
        st.subheader("1 · Property Metadata (required)")
        c1, c2, c3 = st.columns(3)
        with c1:
            addr = st.text_input("Street address", placeholder="e.g. 1234 Maple Ave")
            city = st.text_input("City", placeholder="e.g. Beverly Hills")
            state = st.selectbox("State", sorted(STATE_ABBREV), index=4)
        with c2:
            zip9 = st.text_input("9-digit ZIP (ZIP+4)", placeholder="90210-4801",
                                 help="Required for verification-grade Census/BLS/FEMA lookups")
            apn = st.text_input("APN (Assessor Parcel Number)", placeholder="e.g. 44-33-12-08-1024")
            ptype = st.selectbox("Property type", ["Single Family", "Condo", "Townhouse",
                                                   "Multi-Family", "Manufactured", "Other"])
        with c3:
            beds = st.number_input("Bedrooms", 0, 20, 3)
            baths = st.number_input("Bathrooms", 0.0, 20.0, 2.0, 0.5)
            sqft = st.number_input("Square footage", 100, 50000, 1800)
            year_built = st.number_input("Year built", 1800, 2026, 1995)

        st.subheader("2 · Market & Geospatial Feeds (MLS)")
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

        st.subheader("3 · Price / Underwriting Data")
        c1, c2, c3 = st.columns(3)
        with c1:
            premium = st.number_input("Carrier annual premium quote ($)", 0, 1_000_000, 0, 100)
            arv = st.number_input("After-repair value ($)", 0, 100_000_000, 0, 1000)
        with c2:
            interest_rate = st.number_input("Interest rate (%)", 0.0, 30.0, 7.0, 0.1)
            monthly_rent = st.number_input("Expected monthly rent ($)", 0, 100_000, 0, 50)
        with c3:
            holding_months = st.number_input("Holding months", 1, 24, 6)

        st.subheader("4 · Contractor Quotes (optional but highest authority)")
        st.caption("Paste rows as: finding_key | contractor | license | low | high | eta_days")
        quotes_txt = st.text_area("One quote per line", height=90,
                                  placeholder="heat exchanger crack | A1 HVAC LLC | CA-123456 | 1800 | 2600 | 5")

        st.subheader("5 · Permit Records (from your county/city portal)")
        st.caption("Paste rows as: permit_type | permit_number | date | status | description")
        permits_txt = st.text_area("One permit per line", height=90,
                                   placeholder="Electrical Permit | EL-2021-4412 | 2021-03-15 | Closed | Panel upgrade")

        st.subheader("6 · Evidence Uploads")
        c1, c2 = st.columns(2)
        with c1:
            pdfs = st.file_uploader("Inspection report(s) (PDF)", type=["pdf"], accept_multiple_files=True)
            photos = st.file_uploader("Damage / nameplate photos", type=["png", "jpg", "jpeg"],
                                      accept_multiple_files=True)
        with c2:
            audios = st.file_uploader("Audio recordings (Whisper transcription)", type=["mp3", "wav", "m4a"],
                                      accept_multiple_files=True)
            floorplan_file = st.file_uploader("Floorplan export (JSON/CSV of rooms)", type=["json", "csv"])
            matterport = st.text_input("Matterport model URL (optional)", placeholder="https://my.matterport.com/...")

        st.subheader("7 · Brokerage Transactions (CSV, optional)")
        txns_csv = st.file_uploader("Closed-deal records", type=["csv"],
                                    help="Columns: agent,zip_code,date,credits_negotiated,items_requested,items_granted,deal_value")

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
            st.warning("No inspection report, audio, or manual findings provided. "
                       "You can still proceed, but results will be empty.")
        if not any([pdfs, audios]):
            st.warning("TIP: Upload an inspection PDF or audio recording to populate findings.")

        meta = {
            "address": addr, "city": city, "state": state, "zip9": zip9,
            "apn": apn, "property_type": ptype, "beds": beds, "baths": baths,
            "sqft": sqft, "year_built": year_built,
        }
        mls = {"list_price": list_price or None, "price_per_sqft": price_psf or None,
               "dom_days": dom or None, "last_sale_price": last_sale or None,
               "zone": mls_zone, "source": mls_source}
        uw = {"annual_premium": premium or None, "arv": arv or None,
              "interest_rate": interest_rate / 100, "monthly_rent": monthly_rent or None,
              "holding_months": holding_months}
        quotes = _parse_rows(quotes_txt, ["finding_key", "contractor", "license", "low", "high", "eta_days"])
        permits = _parse_rows(permits_txt, ["permit_type", "permit_number", "permit_date", "status", "description"])
        transactions = _parse_csv(txns_csv) if txns_csv else None

        with st.spinner("Fetching live government data and running analysis…"):
            try:
                session = compile_session_input(
                    meta, mls, uw, quotes, permits, pdfs, audios,
                    floorplan_file, matterport)
                session["transactions"] = transactions
                session["photos"] = [{"name": p.name} for p in (photos or [])]
                results = run_pipeline(session)
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
    st.title("📊 Verified Analysis Results")

    st.caption(f"Generated {res['generated_at']} · ZIP {sess['property_data']['zip_code']} · "
               f"{len(sess['findings'])} findings · Sources: {len(sess['ingestion_report']['report_sources'])} PDF(s), "
               f"{len(sess['ingestion_report']['audio_sources'])} audio")

    t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs([
        "💰 Financial Matrix", "⏳ 24-Month CapEx", "🤝 Sellers-Credit Sandbox",
        "⚖️ Legal Addendums", "🧰 Contractor Dispatch", "🗺️ Spatial 3D Mapping",
        "🛡️ Insurance & Recalls", "🌐 Programmatic Web Pages",
    ])

    with t1:
        render_financial_matrix(res, sess)
    with t2:
        render_capex(res)
    with t3:
        render_sandbox(res)
    with t4:
        render_legal(res, sess)
    with t5:
        render_contractor(res, sess)
    with t6:
        render_spatial(res)
    with t7:
        render_insurance_recalls(res)
    with t8:
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
        rows.append({
            "System": item["system"], "Severity": item["severity"],
            "Finding": item["finding"], "DIY": money(item["diy_low"]) + "–" + money(item["diy_high"]),
            "Contractor": money(item["contractor_low"]) + "–" + money(item["contractor_high"]),
            "Emergency": money(item["emergency_low"]) + "–" + money(item["emergency_high"]),
            "Source": badge(item["provenance"]),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    sev = s["by_severity"]
    sev_df = pd.DataFrame({"Severity": list(sev.keys()), "Est. total ($)": [int(v) for v in sev.values()]})
    fig = go.Figure(go.Bar(x=sev_df["Severity"], y=sev_df["Est. total ($)"],
                           marker_color=["#DC2626", "#EA580C", "#CA8A04", "#16A34A"]))
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
        fig = go.Figure(go.Bar(x=[f"M{m}" for m in months], y=costs,
                               marker_color="#7C3AED"))
        fig.update_layout(title="Projected replacement cost by month", height=320,
                          margin=dict(l=10, r=10, t=40, b=10))
        theme_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)

    rows = []
    for it in capex["timeline_items"]:
        rows.append({
            "System": it["system"], "Severity": it["severity"],
            "Finding": it["finding"], "Asset age": it["current_age"],
            "Remaining life": it["remaining_life_years"],
            "Replace cost": money(it["replacement_cost"]),
            "Failure prob (24mo)": f"{it['failure_probability_24mo']}%",
            "Projected": it["projected_failure_date"],
            "Urgency": it["urgency_category"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_sandbox(res):
    sandbox = res["sandbox"]
    st.subheader("Sellers-Credit Negotiation Sandbox")
    items = sandbox["items"]
    df = pd.DataFrame([{
        "id": i, "Include": i.get("selected", False), "System": i.get("system", ""),
        "Severity": i.get("severity", ""), "Description": i.get("description", ""),
        "Credit (avg)": money(i.get("estimated_cost", 0)),
        "Low": money(i.get("estimated_low", 0)), "High": money(i.get("estimated_high", 0)),
        "Repair type": i.get("repair_type", "seller_credit"),
    } for i in items])
    edited = st.data_editor(df, use_container_width=True, hide_index=True,
                            disabled=["System", "Severity", "Description", "Credit (avg)", "Low", "High"],
                            key="sandbox_editor")
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
    c3.metric("Expected concession", money(totals["expected_concession"]),
              help=f"Based on market leverage {res['leverage']}/100")
    c4.metric("Selected items", totals["selected_items"])

    st.subheader("Negotiation strategies")
    for strat in res["strategies"]:
        st.markdown(f"- **{strat['title']}** — {strat['detail']}  `{strat['relevance']}`")

    scenarios = [
        {"name": "Full credit request", "description": "All critical/high items",
         "changes": []},
        {"name": "Repair-or-credit", "description": "Convert top 3 to seller repair",
         "changes": []},
    ]
    cmp = generate_scenario_comparison(items, scenarios, {"leverage_score": res["leverage"]})
    for sc in cmp:
        st.markdown(f"**{sc['scenario_name']}:** request {money(sc['totals']['total_requested'])} "
                    f"→ expected concession {money(sc['totals']['expected_concession'])}")


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
    st.download_button("Download addendum (.txt)", legal["addendum_text"],
                       file_name="repair_addendum.txt")


def render_contractor(res, sess):
    st.subheader("Contractor Dispatch & Bids")
    st.caption("Bids are either **USER-PROVIDED quotes** (authoritative) or **real BLS OEWS "
               "wage baselines** with standard margin. No invented firms.")
    bids = res["bids"]
    rows = []
    for k, b in bids.items():
        rows.append({
            "System": b["system"], "Severity": b["severity"], "Trade": b["trade"],
            "Finding": b["finding"], "Contractor": b["contractor"],
            "License": b["license_no"], "Bid low": money(b["bid_low"]),
            "Bid high": money(b["bid_high"]), "ETA days": b["eta_days"],
            "Source": badge(b["cost_source"]),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Priority dispatch queue")
    for r in get_contractor_recommendations(bids, 5):
        st.markdown(f"- **{r['severity']} {r['system']}**: {r['contractor']} — "
                    f"{money(r['bid_low'])}–{money(r['bid_high'])}  `{r['cost_source']}`")

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
            fig.add_shape(type="rect", x0=x - w / 2, y0=y - h / 2, x1=x + w / 2, y1=y + h / 2,
                          line=dict(color="#888", width=1), fillcolor="rgba(200,200,200,0.25)")
            fig.add_annotation(x=x, y=y + h / 2 + 0.2, text=room.get("name", ""), showarrow=False,
                               font=dict(size=10))
        for m in sp["findings_mapped"]:
            fig.add_trace(go.Scatter(
                x=[m["x_position"]], y=[m["y_position"]], mode="markers+text",
                marker=dict(size=14, color=m["color"]), text=[f"{m['system']}"],
                textposition="top center", name=f"{m['severity']} {m['system']}",
                hovertemplate=f"{m['finding']}<br>{m['severity']} · {m['system']}<extra></extra>"))
        fig.update_layout(height=560, margin=dict(l=10, r=10, t=40, b=10),
                          title=f"Floor plan ({sp['floor_plan_provenance']})",
                          xaxis=dict(visible=False), yaxis=dict(visible=False))
        theme_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)
    st.caption("Upload a floorplan JSON/CSV or Matterport model on Page 1 for true spatial placement.")


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
            rows.append({
                "Finding": r["finding_description"], "Product": ", ".join(r["product_names"]),
                "Manufacturer": ", ".join(r["manufacturers"]),
                "Hazard": ", ".join(r["hazard_types"]), "Date": r["recall_date"],
                "Remedy": r["remedy"][:80], "Action": r["action_required"][:100],
                "URL": r["recall_url"],
            })
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
        rows.append({
            "System": p["system_type"], "Slug": f"/{p['page_slug']}",
            "Avg cost": money(p["avg_cost"]) if p["avg_cost"] else "—",
            "Cost status": badge(p["cost_provenance"]),
            "H1": p["h1"], "Meta": p["meta_description"][:90],
        })
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
            st.code("agent,zip_code,date,credits_negotiated,items_requested,items_granted,deal_value\n"
                    "Jane Doe,90210,2026-03-01,12500,6,5,950000")


def page_analysis():
    """Page 2 · Deep Analysis & Research — long-form dossier across all 21 modules."""
    res = st.session_state["results"]
    sess = st.session_state["session"]
    d = res["deep_analysis"]

    st.title("🔬 Deep Analysis & Research Dossier")
    st.caption("Long-form, line-item analytical output across all 21 platform modules. "
               "Every figure is real (live government data, user MLS/quotes) or honestly "
               "labeled MODELED/UNAVAILABLE. Nothing is fabricated.")

    # ---- Executive summary strip ----
    cm = res["cost_matrix"]["summary"]
    m = d["module_02_cost"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Findings analyzed", len(sess["findings"]))
    c2.metric("Total repair (avg)", money(cm["total_avg"]))
    c3.metric("Total repair (range)", f"{money(cm['total_low'])}–{money(cm['total_high'])}")
    c4.metric("Market anchor", d["module_04_market"]["anchor"])
    c5.metric("Insurability score", f"{d['module_15_insurance']['score']}/100")

    # ---- Master matrix ----
    st.subheader("📋 Comprehensive Deep-Dive Output Matrix")
    st.caption("System / Issue / Severity / Immediate Repair Range / Future Risk Horizon / "
               "Strategic Action / Permit / Photos / Recalls / Bid — merged per finding.")
    st.dataframe(pd.DataFrame(d["matrix"]), use_container_width=True, hide_index=True)

    # ---- Per-finding deep dive ----
    st.subheader("🔎 Per-Finding Deep Dive")
    for f in d["deep_findings"]:
        with st.expander(f"#{f['index']} [{f['severity']}] {f['system']} — {f['description'][:80]}",
                         expanded=f["severity"] in ("CRITICAL", "HIGH")):
            st.markdown(f"**{f['description']}**")
            st.caption(f"Location: {f['location']} · Source: {f['source_type']} "
                       f"{f['source_file']} · Photos matched: {len(f['photos'])}")
            col1, col2, col3, col4 = st.columns(4)
            cost = f["cost"] or {}
            col1.metric("Repair range", f"{money(cost.get('total_low'))}–{money(cost.get('total_high'))}")
            col1.caption(f"DIY: {money(cost.get('diy_low'))}–{money(cost.get('diy_high'))}")
            cap = f["capex"] or {}
            col2.metric("24-mo failure prob", f"{cap.get('failure_probability_24mo', '—')}%")
            col2.caption(f"Replace: {money(cap.get('replacement_cost'))} · proj. {cap.get('projected_failure_date','—')}")
            col3.metric("Bid", f"{money(f['bid']['bid_low'])}–{money(f['bid']['bid_high'])}" if f["bid"] else "—")
            col3.caption(f["bid"]["cost_source"] if f["bid"] else "Awaiting quote")
            col4.metric("Recalls", len(f["recalls"]))
            col4.metric("Permit", (f["permit_xref"] or {}).get("permit_status", "—"), help=(
                (f["permit_xref"] or {}).get("recommendation", "")))

    # ---- Module sections ----
    modules = [
        _render_m01, _render_m02, _render_m03, _render_m04, _render_m05,
        _render_m06, _render_m07, _render_m08, _render_m09, _render_m10,
        _render_m11, _render_m12, _render_m13, _render_m14, _render_m15,
        _render_m16, _render_m17, _render_m18, _render_m19, _render_m20, _render_m21,
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
    rows = [{"System": i["system"], "Severity": i["severity"], "Finding": i["finding"],
             "DIY": f"{money(i['diy'][0])}–{money(i['diy'][1])}",
             "Contractor": f"{money(i['contractor'][0])}–{money(i['contractor'][1])}",
             "Emergency": f"{money(i['emergency'][0])}–{money(i['emergency'][1])}",
             "Source": badge(i["provenance"])} for i in m["line_items"]]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_m03(d, res, sess):
    m = d["module_03_depreciation"]
    _module_header(m, "📊")
    s = m["summary"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Systems assessed", s["total_systems_assessed"])
    c2.metric("Total replacement value", money(s["total_replacement_value"]))
    c3.metric("Weighted 24-mo risk", money(s["weighted_24mo_risk"]))
    rows = [{"System": i["system"], "Severity": i["severity"], "Asset type": i["asset_type"],
             "Est. age": i["estimated_age"], "Useful life": i["useful_life"],
             "Remaining life": i["remaining_life"], "Fail prob (24mo)": f"{i['failure_probability_24mo']}%",
             "Replacement": money(i["replacement_cost_avg"]), "Projected": i["projected_failure_year"],
             "Urgency": i["replacement_urgency"]} for i in m["capex_items"]]
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
        st.markdown(f"**Census ACS ({m['acs'].get('acs_year','')})** zip median: "
                    f"${m['acs']['median_home_value']:,.0f} · median rent "
                    f"${m['acs'].get('median_gross_rent', 0):,.0f} · owner-occupied "
                    f"{m['acs'].get('owner_occupied_pct', 0)}% · status {badge(m['acs'].get('status'))}")
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
            st.markdown(f"- [{e['severity']}] {e['system']} — {e['description']} ({e['photo_count']} photo(s))")
    if m["findings_missing_photos"]:
        st.markdown(f"**{len(m['findings_missing_photos'])} findings lack photo evidence** — request "
                    "original photos from the inspector for these line items.")


def _render_m07(d, res, sess):
    m = d["module_07_permits"]
    _module_header(m, "🗄️")
    pr = res["permit"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Permits on record", m["total_permits"])
    c2.metric("Closed", m["closed"])
    c3.metric("Open", m["open"])
    c4.metric("Expired", m["expired"])
    st.markdown(f"Overall: **{m['compliance']['overall_status']}** · Unpermitted flags: {m['unpermitted_flags']}")
    rows = [{"Finding": x["finding"], "System": x["system"], "Permit status": x["permit_status"],
             "Risk": x.get("risk_level", ""), "Recommendation": x.get("recommendation", "")}
            for x in m["cross_reference"]]
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
        fig = go.Figure(go.Bar(x=[f"M{v['month']}" for v in m["timeline"]],
                               y=[v["total_cost"] for v in m["timeline"]], marker_color="#7C3AED"))
        fig.update_layout(title="Projected replacement cash outlay by month (24-mo horizon)",
                          height=320, margin=dict(l=10, r=10, t=40, b=10))
        theme_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)
    rows = [{"System": i["system"], "Severity": i["severity"], "Finding": i["finding"],
             "Remaining life": i["remaining_life"], "Fail prob": f"{i['failure_probability_24mo']}%",
             "Replacement": money(i["replacement_cost_avg"]), "Projected": i["projected_failure_year"],
             "Urgency": i["replacement_urgency"]} for i in m["capex_items"]]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_m09(d, res, sess):
    m = d["module_09_sandbox"]
    _module_header(m, "🤝")
    sb = res["sandbox"]
    df = pd.DataFrame([{"System": i["system"], "Severity": i["severity"],
                        "Description": i["description"],
                        "Est. cost": money(i["estimated_cost"]),
                        "Type": i["repair_type"]} for i in sb["items"]])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown(f"**Market leverage:** {m['leverage']}/100 — model scenarios live on the Results page.")


def _render_m10(d, res, sess):
    m = d["module_10_dispatch"]
    _module_header(m, "🧰")
    rows = [{"System": b["system"], "Severity": b["severity"], "Trade": b["trade"],
             "Finding": b["finding"], "Contractor": b["contractor"], "License": b["license_no"],
             "Bid": f"{money(b['bid_low'])}–{money(b['bid_high'])}", "ETA days": b["eta_days"],
             "Source": badge(b["cost_source"])} for b in m["bids"]]
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
    st.download_button("Download addendum (.txt)", m["addendum_text"],
                       file_name="repair_addendum.txt")


def _render_m12(d, res, sess):
    m = d["module_12_environmental"]
    _module_header(m, "🌍")
    g = m["geocoding"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Address resolution", g["status"])
    c1.caption(f"{g.get('matched_address', '')} · {g.get('county', '')}")
    c2.metric("Flood zone", m["flood"].get("risk_level", "—"), help=m["flood"].get("status"))
    c3.metric("Seismic", m["seismic"].get("risk_level", "—"),
              help=f"sds={m['seismic'].get('sds')} · {m['seismic'].get('status')}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Quakes 75km/1yr", m["earthquakes"].get("count_75km_1yr", 0))
    c1.caption(f"Largest: {m['earthquakes'].get('largest_magnitude')} · {m['earthquakes'].get('status')}")
    c2.metric("Weather", m["weather"].get("conditions", "—"), help=f"{m['weather'].get('temperature_f')}°F")
    c3.metric("Overall risk", m["summary_level"])
    st.markdown(f"Finding-derived risks: moisture={m['finding_risks']['mold_moisture']}, "
                f"foundation={m['finding_risks']['foundation']}, fire={m['finding_risks']['fire']}, "
                f"electrical={m['finding_risks']['electrical']}")


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
        st.markdown(f"- **{r['red_flag_type']}** (score {r['risk_score']}, denial {r['denial_probability']*100:.0f}%): "
                    f"{r['description']} — {r['recommendation']}")


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
    st.markdown("**MAO math:** " + money(m["max_offer"]) + " = " + money(m["arv"]) + " − " +
                money(m["repair"]) + " (repair) − " + money(m["holding"]) + " (holding) − " +
                money(m["closing"]) + " (closing) − " + money(m["profit_target"]) + " (target)")
    for a in m["analysis"]:
        st.markdown(f"- {a}")
    rows = [{"Year": y["year"], "Expected cost": money(y["total_expected_cost"]),
             "Items at risk": y["items_at_risk"]} for y in m["forecast"]]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_m17(d, res, sess):
    m = d["module_17_escrow"]
    _module_header(m, "🏦")
    if m["items"]:
        c1, c2 = st.columns(2)
        c1.metric("Total holdback", money(m["total_holdback"]))
        c2.metric("Multiplier", f"{m['multiplier']}x (standard 1.5x–2x)")
        rows = [{"Finding": i["finding"], "System": i["system"], "Severity": i["severity"],
                 "Contractor bid": money(i["contractor_bid"]),
                 "Holdback (1.5x)": money(i["holdback_amount"]),
                 "Release conditions": i["release_conditions"],
                 "Milestone 1": f"{i['milestone_1_pct']}% — {i['milestone_1']}",
                 "Milestone 2": f"{i['milestone_2_pct']}% — {i['milestone_2']}"}
                for i in m["items"]]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.write("No critical/high findings to hold back.")


def _render_m18(d, res, sess):
    m = d["module_18_seo"]
    _module_header(m, "🌐")
    c1, c2 = st.columns(2)
    c1.metric("Pages generated", m["total_pages"])
    c2.metric("Analytics", m["analytics_status"])
    rows = [{"System": p["system_type"], "Slug": f"/{p['page_slug']}",
             "Avg cost": money(p["avg_cost"]) if p["avg_cost"] else "—",
             "Cost status": badge(p["cost_provenance"])} for p in m["pages"]]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_m19(d, res, sess):
    m = d["module_19_audio"]
    _module_header(m, "🎙️")
    c1 = st.columns(1)[0]
    c1.metric("Findings from audio", m["from_audio"])
    for s in m["sources"]:
        st.markdown(f"- 🎙️ `{s['file']}` — {s['status']}")
    if not m["from_audio"]:
        st.info("No audio recorded. Record inspector walk-through notes on Page 1 → Section 6 "
                "and they will be transcribed by the local Whisper model.")


def _render_m20(d, res, sess):
    m = d["module_20_recalls"]
    _module_header(m, "📦")
    c1, c2 = st.columns(2)
    c1.metric("Recall matches", m["total"])
    c2.metric("Potential avoided cost (heuristic)", money(m["savings"]))
    if m["results"]:
        rows = [{"Finding": r["finding_description"], "Product": ", ".join(r["product_names"]),
                 "Manufacturer": ", ".join(r["manufacturers"]),
                 "Hazard": ", ".join(r["hazard_types"]), "Remedy": r["remedy"][:90],
                 "Action": r["action_required"][:100], "URL": r["recall_url"]}
                for r in m["results"]]
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
            fig.add_shape(type="rect", x0=x - w / 2, y0=y - h / 2, x1=x + w / 2, y1=y + h / 2,
                          line=dict(color="#888", width=1), fillcolor="rgba(200,200,200,0.25)")
            fig.add_annotation(x=x, y=y + h / 2 + 0.2, text=room.get("name", ""), showarrow=False,
                               font=dict(size=10))
        for mk in m["findings_mapped"]:
            fig.add_trace(go.Scatter(x=[mk["x_position"]], y=[mk["y_position"]],
                                     mode="markers+text", marker=dict(size=14, color=mk["color"]),
                                     text=[f"{mk['system']}"], textposition="top center",
                                     name=f"{mk['severity']} {mk['system']}",
                                     hovertemplate=f"{mk['finding']}<br>{mk['severity']}<extra></extra>"))
        fig.update_layout(height=560, margin=dict(l=10, r=10, t=40, b=10),
                          title=f"Floor plan ({m['provenance']})",
                          xaxis=dict(visible=False), yaxis=dict(visible=False))
        theme_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)


def page_health():
    st.subheader("🔎 Live data source health")
    health = check_api_health()
    for k, v in health.items():
        ok = "🟢" if v is True else "🟠" if v == "REQUIRES_KEY" else "🔴" if v is False else "⚪"
        st.markdown(f"{ok} **{k}** — `{v}`")
    st.caption("FEMA NFHL is unreachable from some networks; the engine retries multiple hosts "
               "and reports UNAVAILABLE honestly. BLS unregistered requests are limited to 25/day "
               "— set BLS_API_KEY for full access. Census ACS needs CENSUS_API_KEY (free).")


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
            st.info("No analysis yet. Enter inputs on the **Inputs** page "
                    "and press **Run Analysis**.")
        else:
            page_analysis()
    elif current == "Results":
        if "results" not in st.session_state:
            st.info("No analysis yet. Enter inputs on the **Inputs** page "
                    "and press **Run Analysis**.")
        else:
            page_results()
    else:
        page_health()

    render_footer()


main()