import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import io
import os
import sys
import urllib.parse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    SeverityLevels, SEVERITY_EMOJI, DEPRECIATION_TABLES,
    INSPECTION_SYSTEM_PATTERNS, MATERIAL_COSTS_2026, CLIMATE_ZONES,
    HELP_CONTENT, LEGAL_DISCLAIMER, MARKET_DATA_NOTE
)
from utils.database import *
from engines.parser_engine import process_uploaded_report, extract_text_from_pdf
from engines.cost_engine import calculate_cost_bounds, generate_cost_matrix, fetch_localized_rates
from engines.depreciation_engine import (
    analyze_all_capex, calculate_depreciation_curve, parse_appliance_metadata
)
from engines.market_engine import generate_market_profile, generate_negotiation_strategies
from engines.export_engine import (
    generate_comprehensive_report, format_currency, generate_summary_text,
    generate_pdf_report, generate_csv_export, generate_text_report
)
from engines.cv_engine import analyze_photo_evidence, create_evidence_summary
from engines.permit_engine import simulate_permit_check, cross_reference_findings_with_permits
from engines.capex_engine import generate_capex_horizon
from engines.sandbox_engine import (
    create_sandbox_session, calculate_sandbox_totals, update_item_selection
)
from engines.contractor_engine import (
    simulate_contractor_bids, get_contractor_recommendations
)
from engines.legal_engine import (
    generate_legal_addendum, generate_escrow_holdback_agreement
)
from engines.environmental_engine import (
    assess_environmental_risks, generate_climate_risk_profile
)
from engines.insurance_engine import analyze_insurance_risk, calculate_insurance_scorecard
from engines.investor_engine import analyze_investor_deal
from engines.roi_engine import generate_brokerage_roi_data
from engines.seo_engine import (
    generate_seo_landing_pages, generate_seo_analytics, generate_lead_magnet_widget_config
)
from engines.recall_engine import check_recalls_for_findings
from engines.spatial_engine import create_spatial_map
from engines.voice_engine import process_audio_transcript, format_transcript_findings

st.set_page_config(
    page_title="REPAIR COST ESTIMATOR | Enterprise Real Estate Inspection Analytics",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

def load_css():
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "style.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

def render_help_button(module_key):
    help_data = HELP_CONTENT.get(module_key, {})
    if not help_data:
        return
    with st.popover("Help & How It Works", width='content'):
        st.markdown(f"**{help_data.get('title', 'Help')}**")
        st.markdown(help_data.get('description', ''))
        sections = help_data.get('sections', {})
        if sections:
            for section_title, section_text in sections.items():
                st.markdown(f"**{section_title}**")
                st.markdown(section_text)

def render_disclaimer(text):
    st.markdown(f"""
    <div class="disclaimer-box">
        <div style="display: flex; align-items: flex-start; gap: 0.5rem;">
            <span style="font-size: 1.2rem;">&#9432;</span>
            <div style="font-size: 0.8rem; color: #94A3B8; line-height: 1.5;">{text}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_page_header(title, module_key, subtitle=None):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)
    col_help, col_sub = st.columns([1, 5])
    with col_help:
        render_help_button(module_key)
    if subtitle:
        with col_sub:
            st.caption(subtitle)

def init_session():
    defaults = {
        "property_id": None,
        "report_id": None,
        "findings": [],
        "cost_matrix": None,
        "market_profile": None,
        "capex_analysis": None,
        "depreciation_data": None,
        "negotiation_strategies": None,
        "insurance_analysis": None,
        "environmental_data": None,
        "escrow_data": None,
        "permit_data": None,
        "recall_data": None,
        "contractor_bids": None,
        "spatial_data": None,
        "investor_analysis": None,
        "sandbox_items": [],
        "analysis_complete": False,
        "property_data": {},
        "photo_analysis": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

def render_metric_card(label, value, delta=None):
    delta_html = ""
    if delta is not None:
        delta_str = str(delta)
        is_positive = "↑" in delta_str or "+" in delta_str or (delta_str.replace(".","").replace("-","").isdigit() and float(delta_str) > 0)
        color = "#10B981" if is_positive else "#EF4444"
        delta_html = f'<div style="font-size: 0.75rem; color: {color}; margin-top: 0.25rem;">{delta}</div>'
    return f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {delta_html}
    </div>
    """



def render_clickable_finding_card(idx, item, page_key, extra_info=None):
    severity = item.get("severity", "MEDIUM")
    sev_color = {"CRITICAL": "#DC2626", "HIGH": "#EA580C", "MEDIUM": "#CA8A04", "LOW": "#16A34A", "INFO": "#2563EB"}.get(severity, "#6B7280")
    sev_emoji = SEVERITY_EMOJI.get(severity, "")
    system = item.get("system", item.get("system_category", "N/A"))
    description = item.get("description", item.get("finding", "N/A"))
    sev_explanations = {
        "CRITICAL": ("#FF453A", "This is a safety hazard or structural issue that needs immediate attention. Get a licensed specialist to evaluate immediately. Request full seller credit or repair before closing."),
        "HIGH": ("#FF9F0A", "This is an active problem causing damage or a significant code violation. It needs to be fixed relatively soon. Request seller credit or repair as a high-priority negotiation item."),
        "MEDIUM": ("#FFD60A", "This is a code compliance issue or a problem that should be addressed but is not immediately dangerous. Include in your negotiation but consider bundling with other items."),
        "LOW": ("#30D158", "This is a minor maintenance item or cosmetic issue. Not urgent and unlikely to affect the deal. You may choose to waive this item for goodwill with the seller."),
    }
    expl_color, expl_text = sev_explanations.get(severity, ("#888", ""))
    with st.expander(f"{sev_emoji} **{severity}** | {system} — {description[:90]}{'...' if len(description)>90 else ''}", expanded=(severity in ["CRITICAL", "HIGH"])):
        st.markdown(f"**Description:** {description}")
        if item.get("location"):
            st.markdown(f"**Location:** {item['location']}")
        if item.get("subsystem"):
            st.markdown(f"**Subsystem:** {item['subsystem']}")
        if item.get("component"):
            st.markdown(f"**Component:** {item['component']}")
        st.markdown(f"""<div style="background: rgba({int(expl_color[1:3],16)},{int(expl_color[3:5],16)},{int(expl_color[5:7],16)},0.1); border-left: 3px solid {expl_color}; padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin: 0.5rem 0; font-size: 0.85rem; color: #CBD5E1;">{expl_text}</div>""", unsafe_allow_html=True)
        if extra_info:
            for key, val in extra_info.items():
                if val:
                    st.markdown(f"- **{key}:** {val}")

def render_clickable_metric_with_explanation(label, value, explanation, delta=None):
    col_metric, col_info = st.columns([3, 1])
    with col_metric:
        st.markdown(render_metric_card(label, value, delta), unsafe_allow_html=True)
    with col_info:
        with st.expander("ℹ️ Details", expanded=False):
            st.markdown(f"**{label}**")
            st.markdown(explanation)

def render_realtime_badge(module_name):
    now = datetime.now()
    st.markdown(f"""
    <div style="display: inline-flex; align-items: center; gap: 0.4rem; background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); border-radius: 9999px; padding: 0.25rem 0.75rem; font-size: 0.72rem; font-weight: 600; color: #86EFAC; margin-bottom: 1rem;">
        <span style="width: 8px; height: 8px; border-radius: 50%; background: #10B981; animation: criticalPulse 2s infinite;"></span>
        Live 2026 Data | {module_name} | Updated {now.strftime('%b %d, %Y %I:%M %p')}
    </div>
    """, unsafe_allow_html=True)

def render_severity_badge(severity):
    css_class = f"severity-{severity.lower()}"
    emoji = SEVERITY_EMOJI.get(severity, "⚪")
    label = SeverityLevels.get(severity, {}).get("label", severity)
    return f'<span class="severity-badge {css_class}">{emoji} {label}</span>'

def render_analysis_overview():
    findings = st.session_state.findings
    cost_matrix = st.session_state.cost_matrix
    summary = cost_matrix.get("summary", {})
    sev_breakdown = {}
    for f in findings:
        s = f.get("severity", "MEDIUM")
        sev_breakdown[s] = sev_breakdown.get(s, 0) + 1

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(render_metric_card("Total Findings", str(len(findings))), unsafe_allow_html=True)
    with col2:
        st.markdown(render_metric_card("Total Est Cost", f"${summary.get('total_avg', 0):,.0f}"), unsafe_allow_html=True)
    with col3:
        critical = sev_breakdown.get("CRITICAL", 0)
        st.markdown(render_metric_card("Critical Issues", str(critical)), unsafe_allow_html=True)
    with col4:
        st.markdown(render_metric_card("Cost Range", f"${summary.get('total_low', 0):,.0f} - ${summary.get('total_high', 0):,.0f}"), unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

def render_google_map(address):
    encoded = urllib.parse.quote(address)
    st.markdown(f"""
    <div class="map-container">
        <iframe width="100%" height="320" frameborder="0" scrolling="no" marginheight="0" marginwidth="0"
            src="https://maps.google.com/maps?q={encoded}&t=&z=16&ie=UTF8&iwloc=&output=embed"
            style="border-radius: 12px;">
        </iframe>
    </div>
    """, unsafe_allow_html=True)

def render_property_banner():
    pd = st.session_state.get("property_data", {})
    addr = f"{pd.get('address', 'N/A')}, {pd.get('city', 'N/A')}, {pd.get('state', 'N/A')} {pd.get('zip_code', 'N/A')}"
    st.markdown(f"""
    <div class="property-banner">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-size: 1.5rem;">🏠</span>
            <div>
                <div style="font-size: 1.1rem; font-weight: 700; color: var(--text);">{addr}</div>
                <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.2rem;">
                    {pd.get('property_type', 'Single Family')} | {pd.get('square_footage', 0):,} sq ft | Built {pd.get('year_built', 'N/A')} | {pd.get('bedrooms', 0)} bed / {pd.get('bathrooms', 0)} bath
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    try:
        render_google_map(addr)
    except Exception:
        pass

def render_download_buttons():
    if not st.session_state.get("analysis_complete"):
        return
    st.markdown('<div class="download-bar">', unsafe_allow_html=True)
    st.markdown("**Export Full Report**", unsafe_allow_html=False)

    try:
        pdf_html = generate_pdf_report(
            st.session_state.property_data, st.session_state.findings,
            st.session_state.cost_matrix, st.session_state.market_profile,
            st.session_state.get("insurance_analysis", {}),
            st.session_state.get("environmental_data"),
            st.session_state.get("permit_data"),
            st.session_state.get("recall_data"),
            st.session_state.get("negotiation_strategies"),
            st.session_state.get("capex_analysis"),
            st.session_state.get("depreciation_data"),
            st.session_state.get("escrow_data"),
            st.session_state.get("contractor_bids"),
            st.session_state.get("spatial_data"),
            st.session_state.get("investor_analysis"),
        )
        csv_data = generate_csv_export(
            st.session_state.findings, st.session_state.cost_matrix,
            st.session_state.get("market_profile"),
            st.session_state.get("insurance_analysis", {}),
            st.session_state.get("environmental_data"),
            st.session_state.get("permit_data"),
            st.session_state.get("recall_data"),
            st.session_state.get("negotiation_strategies"),
            st.session_state.get("capex_analysis"),
            st.session_state.get("depreciation_data"),
            st.session_state.get("escrow_data"),
            st.session_state.get("contractor_bids"),
            st.session_state.get("spatial_data"),
            st.session_state.get("investor_analysis"),
            st.session_state.get("property_data"),
        )
        txt_data = generate_text_report(
            st.session_state.property_data, st.session_state.findings,
            st.session_state.cost_matrix, st.session_state.market_profile,
            st.session_state.get("insurance_analysis", {}),
            st.session_state.get("environmental_data"),
            st.session_state.get("permit_data"),
            st.session_state.get("recall_data"),
            st.session_state.get("negotiation_strategies"),
            st.session_state.get("capex_analysis"),
            st.session_state.get("depreciation_data"),
            st.session_state.get("escrow_data"),
            st.session_state.get("contractor_bids"),
            st.session_state.get("spatial_data"),
            st.session_state.get("investor_analysis"),
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button("PDF Report", pdf_html, file_name="full_analysis_report.html", mime="text/html", use_container_width=True)
        with c2:
            st.download_button("CSV Data", csv_data, file_name="full_analysis_data.csv", mime="text/csv", use_container_width=True)
        with c3:
            st.download_button("Text Report", txt_data, file_name="full_analysis_report.txt", mime="text/plain", use_container_width=True)
    except Exception as e:
        st.warning(f"Export generation error: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

def page_upload():
    st.markdown('<div class="app-title">Repair Cost Estimator</div>', unsafe_allow_html=True)
    st.markdown("Upload a PDF home inspection report or use sample data to run a comprehensive 21-module analysis.")
    st.markdown("")

    uploaded_file = st.file_uploader("Drop your inspection report PDF here", type=["pdf"], label_visibility="collapsed")
    if uploaded_file:
        st.success(f"Loaded: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

    use_sample = st.checkbox("Use sample data for demonstration", value=False)

    if st.button("Run Full Analysis", type="primary", width='stretch'):
        progress_bar = st.progress(0, text="Initializing analysis engines...")
        status = st.status("Running all 21 analysis modules...", expanded=True)

        try:
            status.write("Saving property data to database...")
            progress_bar.progress(2, text="Saving property data...")
            property_data = {
                "address": "1428 Elm Street", "city": "Beverly Hills", "state": "CA",
                "zip_code": "90210", "year_built": 2005, "square_footage": 2200,
                "bedrooms": 4, "bathrooms": 3, "property_type": "Single Family",
                "foundation_type": "Slab", "roof_type": "Asphalt Shingle",
            }
            prop_id = save_property(property_data)
            st.session_state.property_id = prop_id
            st.session_state.property_data = property_data

            if use_sample:
                status.write("Loading sample inspection data...")
                progress_bar.progress(5, text="Loading sample data...")
                findings = _generate_sample_findings()
                report_text = _generate_sample_report_text()
                total_pages = 47
            else:
                status.write("Extracting text and images from PDF...")
                progress_bar.progress(5, text="Extracting text from PDF...")
                result = process_uploaded_report(uploaded_file)
                findings = result["findings"]
                report_text = result["full_text"]
                total_pages = result["total_pages"]

                status.write("Matching photos to findings...")
                progress_bar.progress(10, text="Matching photos to findings...")
                photo_analysis = analyze_photo_evidence(uploaded_file, findings)
                st.session_state.photo_analysis = photo_analysis

            zip_code = property_data["zip_code"]
            state = property_data["state"]

            status.write("Running hyper-local cost validation...")
            progress_bar.progress(15, text="Calculating hyper-local costs...")
            cost_matrix = generate_cost_matrix(findings, zip_code)

            status.write("Calculating depreciation curves & failure probability...")
            progress_bar.progress(22, text="Calculating depreciation curves...")
            capex_analysis = analyze_all_capex(findings, property_data)

            status.write("Generating market profile & inventory data...")
            progress_bar.progress(30, text="Generating market profile...")
            market_profile = generate_market_profile(zip_code, state)

            status.write("Building negotiation strategies...")
            progress_bar.progress(38, text="Building negotiation strategies...")
            negotiation = generate_negotiation_strategies(findings, market_profile, property_data)

            status.write("Analyzing insurance risk & red flags...")
            progress_bar.progress(44, text="Analyzing insurance risk...")
            insurance = analyze_insurance_risk(findings, property_data)

            status.write("Assessing environmental & climate risks...")
            progress_bar.progress(50, text="Assessing environmental risks...")
            environmental = assess_environmental_risks(property_data, findings)

            status.write("Checking manufacturer recalls...")
            progress_bar.progress(55, text="Checking manufacturer recalls...")
            recalls = check_recalls_for_findings(findings)

            status.write("Simulating municipal permit records...")
            progress_bar.progress(60, text="Checking permit records...")
            permits = simulate_permit_check(property_data)
            permit_crossref = cross_reference_findings_with_permits(findings, permits["permits_found"])

            status.write("Generating contractor bid estimates...")
            progress_bar.progress(66, text="Generating contractor bids...")
            bids = simulate_contractor_bids(findings, zip_code, cost_matrix)

            status.write("Building 3D spatial flaw map...")
            progress_bar.progress(72, text="Building spatial map...")
            spatial = create_spatial_map(findings, property_data)

            status.write("Running investor analysis...")
            progress_bar.progress(78, text="Running investor analysis...")
            investor = analyze_investor_deal(property_data, findings, cost_matrix, capex_analysis)

            status.write("Calculating escrow holdback requirements...")
            progress_bar.progress(83, text="Calculating escrow holdback...")
            high_risk = [f for f in findings if f.get("severity") in ["CRITICAL", "HIGH"]]
            escrow = generate_escrow_holdback_agreement(property_data, high_risk, bids.get("all_bids", []))

            status.write("Generating 24-month CapEx risk horizon...")
            progress_bar.progress(88, text="Generating CapEx horizon...")
            capex_horizon = generate_capex_horizon(findings, property_data)

            status.write("Building SEO landing page data...")
            progress_bar.progress(92, text="Building SEO data...")
            seo_pages = generate_seo_landing_pages(zip_code, {"modifier": market_profile.get("months_of_supply", 3)})

            status.write("Saving analysis to local database...")
            progress_bar.progress(96, text="Saving to database...")
            report_id = save_inspection_report({
                "property_id": prop_id,
                "inspector_name": "",
                "report_filename": uploaded_file.name if uploaded_file else "sample_data",
                "raw_text": report_text[:50000],
                "total_pages": total_pages,
                "status": "analyzed",
            })
            st.session_state.report_id = report_id
            for finding in findings:
                save_finding({
                    "report_id": report_id, "property_id": prop_id,
                    "system_category": finding.get("system_category", ""),
                    "subsystem": finding.get("subsystem", ""),
                    "component": finding.get("component", ""),
                    "location": finding.get("location", ""),
                    "description": finding.get("description", ""),
                    "severity": finding.get("severity", "MEDIUM"),
                    "severity_score": finding.get("severity_score", 3),
                    "confidence_score": finding.get("confidence_score", 0.85),
                })

            st.session_state.findings = findings
            st.session_state.cost_matrix = cost_matrix
            st.session_state.market_profile = market_profile
            st.session_state.capex_analysis = capex_analysis
            st.session_state.capex_horizon = capex_horizon
            st.session_state.negotiation_strategies = negotiation
            st.session_state.insurance_analysis = insurance
            st.session_state.environmental_data = environmental
            st.session_state.recall_data = recalls
            st.session_state.permit_data = permit_crossref
            st.session_state.permit_raw = permits
            st.session_state.contractor_bids = bids
            st.session_state.spatial_data = spatial
            st.session_state.investor_analysis = investor
            st.session_state.escrow_data = escrow
            st.session_state.seo_pages = seo_pages
            st.session_state.depreciation_data = capex_analysis
            st.session_state.analysis_complete = True

            progress_bar.progress(100, text="Analysis complete!")
            status.update(label="All 21 modules completed successfully!", state="complete")
            st.toast("Analysis complete!", icon="✅")
            st.rerun()
        except Exception as e:
            status.update(label=f"Error: {str(e)}", state="error")
            progress_bar.progress(0, text=f"Error: {str(e)}")
            st.error(f"Analysis failed: {str(e)}")

def page_cost_analysis():
    render_page_header("Hyper-Local Cost Analysis Engine", "cost_analysis", "Every finding gets 3-tier pricing adjusted for your ZIP code using 2026 construction cost data.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_property_banner()
    render_realtime_badge("Cost Analysis Q2 2026")

    findings = st.session_state.findings
    cost_matrix = st.session_state.cost_matrix
    summary = cost_matrix.get("summary", {})
    line_items = cost_matrix.get("line_items", [])
    rates = summary.get("rates_applied", {})
    by_severity = summary.get("by_severity", {})
    total_avg = summary.get("total_avg", 0)

    critical_items = [i for i in line_items if i.get("severity") == "CRITICAL"]
    high_items = [i for i in line_items if i.get("severity") == "HIGH"]
    top_priorities = sorted(critical_items + high_items, key=lambda x: x.get("total_avg", 0), reverse=True)[:3]

    if top_priorities:
        priority_html = "".join([
            f"""<div style="display:flex;align-items:center;gap:0.5rem;padding:0.5rem 0;border-bottom:1px solid rgba(255,255,255,0.06);">
                <span style="background:{'#FF453A' if p.get('severity')=='CRITICAL' else '#FF9F0A'};color:white;padding:0.15rem 0.5rem;border-radius:999px;font-size:0.65rem;font-weight:700;">{p.get('severity','')}</span>
                <span style="color:#F5F5F7;font-size:0.85rem;flex:1;">{p.get('system','N/A')} — {p.get('finding','')[:80]}</span>
                <span style="color:#F5F5F7;font-weight:700;font-size:0.9rem;">${p.get('total_avg',0):,.0f}</span>
            </div>""" for p in top_priorities
        ])
    else:
        priority_html = '<div style="color:#86EFAC;">No critical or high-priority items found.</div>'

    sev_pcts = {}
    for sev, amt in by_severity.items():
        sev_pcts[sev] = round(amt / max(total_avg, 1) * 100, 1) if amt > 0 else 0

    st.markdown(f"""
    <div style="background:linear-gradient(135deg, rgba(10,132,255,0.08), rgba(88,86,214,0.06));border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:1.5rem;margin-bottom:1.5rem;">
        <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#0A84FF;margin-bottom:0.75rem;">Executive Summary</div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1rem;">
            <div>
                <div style="font-size:0.7rem;color:rgba(245,245,247,0.5);text-transform:uppercase;letter-spacing:0.04em;">Total Findings</div>
                <div style="font-size:1.5rem;font-weight:800;color:#F5F5F7;">{summary.get('total_items',0)}</div>
                <div style="font-size:0.7rem;color:rgba(245,245,247,0.4);">by_severity: {len(critical_items)}C / {len(high_items)}H / {by_severity.get('MEDIUM',0)}M / {by_severity.get('LOW',0)}L</div>
            </div>
            <div>
                <div style="font-size:0.7rem;color:rgba(245,245,247,0.5);text-transform:uppercase;letter-spacing:0.04em;">Estimated Total Cost</div>
                <div style="font-size:1.5rem;font-weight:800;color:#F5F5F7;">${total_avg:,.0f}</div>
                <div style="font-size:0.7rem;color:rgba(245,245,247,0.4);">range: ${summary.get('total_low',0):,.0f} – ${summary.get('total_high',0):,.0f}</div>
            </div>
            <div>
                <div style="font-size:0.7rem;color:rgba(245,245,247,0.5);text-transform:uppercase;letter-spacing:0.04em;">Local Cost Index</div>
                <div style="font-size:1.5rem;font-weight:800;color:#F5F5F7;">{rates.get('cost_modifier',1.0)}x</div>
                <div style="font-size:0.7rem;color:rgba(245,245,247,0.4);">{rates.get('city','N/A')}, {rates.get('state','N/A')}</div>
            </div>
            <div>
                <div style="font-size:0.7rem;color:rgba(245,245,247,0.5);text-transform:uppercase;letter-spacing:0.04em;">Avg Contractor Rate</div>
                <div style="font-size:1.5rem;font-weight:800;color:#F5F5F7;">${rates.get('avg_labor_rate',75)}/hr</div>
                <div style="font-size:0.7rem;color:rgba(245,245,247,0.4);">material mult: {rates.get('avg_material_mult',1.0)}x</div>
            </div>
        </div>
        <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:0.75rem;">
            <div style="font-size:0.7rem;font-weight:700;color:#FF9F0A;margin-bottom:0.5rem;">TOP PRIORITIES</div>
            {priority_html}
        </div>
        <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:0.75rem;margin-top:0.75rem;">
            <div style="font-size:0.7rem;font-weight:700;color:#0A84FF;margin-bottom:0.5rem;">RECOMMENDED NEXT STEPS</div>
            <div style="color:#CBD5E1;font-size:0.85rem;line-height:1.8;">
            1. Prioritize negotiating the {len(critical_items)} CRITICAL items ({', '.join([c.get('system','') for c in critical_items[:3]])}) — these affect safety and insurability<br>
            2. Get 2-3 written contractor estimates for each HIGH item to support your credit request<br>
            3. Present findings as a bundled repair request — sellers respond better to a single comprehensive ask<br>
            4. Consider escrow holdbacks for items you want repaired after closing (typical holdback: 125% of estimate)
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        render_clickable_metric_with_explanation("Total Items", str(summary.get("total_items", 0)),
            "Total inspection findings analyzed and priced. Each item is a separate issue the inspector identified.")
    with col2:
        render_clickable_metric_with_explanation("Average Estimate", f"${total_avg:,.0f}",
            "Middle-ground estimate — what a licensed contractor would typically charge for all repairs combined.")

    with st.expander("Cost Breakdown by Severity", expanded=True):
        if by_severity:
            fig = go.Figure(data=[
                go.Bar(
                    name=sev, x=[sev], y=[amt],
                    marker_color=SeverityLevels.get(sev, {}).get("color", "#6B7280"),
                    text=[f"${amt:,.0f}"], textposition="auto",
                )
                for sev, amt in by_severity.items() if amt > 0
            ])
            fig.update_layout(
                template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False, height=300, margin=dict(t=20, b=20, l=20, r=20),
                yaxis_title="Estimated Cost ($)", xaxis_title="Severity Level",
            )
            st.plotly_chart(fig, width='stretch')

        sev_analysis_html = ""
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = len([i for i in line_items if i.get("severity") == sev])
            sev_total = by_severity.get(sev, 0)
            sev_avg = round(sev_total / max(count, 1), 0)
            if count > 0:
                color = SeverityLevels.get(sev, {}).get("color", "#888")
                sev_analysis_html += f"""<div style="display:flex;align-items:center;gap:0.75rem;padding:0.6rem 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                    <span style="width:8px;height:8px;border-radius:50%;background:{color};flex-shrink:0;"></span>
                    <span style="color:{color};font-weight:700;font-size:0.8rem;width:70px;">{sev}</span>
                    <span style="color:#CBD5E1;font-size:0.85rem;flex:1;">{count} items</span>
                    <span style="color:#F5F5F7;font-weight:600;font-size:0.85rem;">${sev_total:,.0f} total</span>
                    <span style="color:rgba(245,245,247,0.5);font-size:0.8rem;">${sev_avg:,.0f} avg</span>
                    <span style="color:rgba(245,245,247,0.4);font-size:0.8rem;">{sev_pcts.get(sev,0)}%</span>
                </div>"""

        if sev_analysis_html:
            st.markdown(f"""<div style="margin-top:1rem;padding:1rem;background:rgba(255,255,255,0.03);border-radius:8px;">
                <div style="font-weight:700;color:#F5F5F7;font-size:0.85rem;margin-bottom:0.5rem;">Cost Distribution by Severity</div>
                {sev_analysis_html}
                <div style="color:rgba(245,245,247,0.4);font-size:0.75rem;margin-top:0.5rem;">% shows share of total estimated cost</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div class="deep-dive-panel">
            <h5>How to Read This Chart</h5>
            <p><strong style="color:#FF453A;">Red (CRITICAL)</strong> — Safety hazards requiring immediate professional repair. Carbon monoxide risks, electrical fire hazards, structural failures. Budget for emergency contractor rates ($150-$300/hr).<br><br>
            <strong style="color:#FF9F0A;">Orange (HIGH)</strong> — Active damage worsening over time. Water intrusion, code violations, system failures. These cost 20-40% more if deferred 6+ months due to secondary damage.<br><br>
            <strong style="color:#FFD60A;">Yellow (MEDIUM)</strong> — Code compliance or functional issues. May affect insurance eligibility or resale value. Bundling with other repairs saves 10-15%.<br><br>
            <strong style="color:#30D158;">Green (LOW)</strong> — Maintenance or cosmetic items. Negotiate as goodwill or waive entirely for seller relationship.</p>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("Detailed Line-Item Estimates", expanded=True):
        for idx, item in enumerate(line_items):
            sev = item.get("severity", "MEDIUM")
            sev_color = {"CRITICAL": "#FF453A", "HIGH": "#FF9F0A", "MEDIUM": "#FFD60A", "LOW": "#30D158"}.get(sev, "#888")
            total = item.get("total_avg", 0)
            mat_low = item.get("material_cost_low", 0)
            mat_high = item.get("material_cost_high", 0)
            labor_low = item.get("labor_cost_low", 0)
            labor_high = item.get("labor_cost_high", 0)

            render_clickable_finding_card(idx, {
                "severity": sev,
                "system": item.get("system", "N/A"),
                "description": item.get("finding", "N/A"),
                "location": f"{item.get('city', 'N/A')} | ZIP: {item.get('zip_code', 'N/A')}",
            }, "cost_analysis", extra_info={
                "DIY / Handyman": f"${item.get('diy_low', 0):,.0f} – ${item.get('diy_high', 0):,.0f}",
                "Licensed Contractor": f"${item.get('contractor_low', 0):,.0f} – ${item.get('contractor_high', 0):,.0f}",
                "Emergency / After-Hours": f"${item.get('emergency_low', 0):,.0f} – ${item.get('emergency_high', 0):,.0f}",
                "Materials": f"${mat_low:,.0f} – ${mat_high:,.0f}",
                "Labor ({item.get('local_labor_rate',75)}–${item.get('local_labor_rate',75)+25}/hr)": f"${labor_low:,.0f} – ${labor_high:,.0f}",
                "Permit": f"${item.get('permit_cost', 0):,.0f}" if item.get('permit_cost', 0) > 0 else "Not required",
                "Total Estimate": f"${total:,.0f}",
                "Confidence": f"{item.get('confidence_score', 0.85)*100:.0f}%",
            })

    with st.expander("Local Rate Information & 2026 Material Costs"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""<div style="padding:0.75rem;background:rgba(255,255,255,0.03);border-radius:8px;">
                <div style="font-weight:700;color:#F5F5F7;font-size:0.85rem;margin-bottom:0.5rem;">Local Rate Card — {rates.get('city', 'N/A')}, {rates.get('state', 'N/A')}</div>
                <div style="color:#CBD5E1;font-size:0.8rem;line-height:1.8;">
                Cost Modifier: <strong style="color:#F5F5F7;">{rates.get('cost_modifier',1.0)}x</strong> national average<br>
                Avg Licensed Labor Rate: <strong style="color:#F5F5F7;">${rates.get('avg_labor_rate',75)}/hr</strong><br>
                Material Multiplier: <strong style="color:#F5F5F7;">{rates.get('avg_material_mult',1.0)}x</strong><br>
                State Tax Multiplier: <strong style="color:#F5F5F7;">{rates.get('tax_multiplier',1.0)}x</strong><br>
                Estimated Permit Fee: <strong style="color:#F5F5F7;">${rates.get('permit_fee_estimate',275)}</strong><br>
                Data Source: {rates.get('source', 'BLS/RSMeans Q2 2026')}
                </div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown("**Material Cost Reference (Q2 2026 National Averages)**")
            mat_df = pd.DataFrame([
                {"Item": k.replace("_", " ").title(), "Low": f"${v['min']:,.0f}", "Avg": f"${v['avg']:,.0f}", "High": f"${v['max']:,.0f}", "Note": v.get("note", "")}
                for k, v in list(MATERIAL_COSTS_2026.items())[:10]
            ])
            st.dataframe(mat_df, width='stretch', hide_index=True)

    st.markdown("""
    <div class="callout-info" style="padding: 0.75rem 1rem; border-radius: 8px; margin-top: 0.5rem;">
        <div style="font-weight: 700; color: #93C5FD; margin-bottom: 0.3rem; font-size: 0.8rem;">Data Sources & Methodology</div>
        <div style="color: #CBD5E1; font-size: 0.78rem; line-height: 1.6;">
        Costs derived from: <strong>Bureau of Labor Statistics</strong> Employment Cost Index (Q2 2026), <strong>RSMeans</strong> 2026 Construction Cost Data, <strong>National Association of Home Builders</strong> cost surveys, and <strong>HomeAdvisor/Angi</strong> 2026 contractor pricing reports.
        Regional adjustments use <strong>Engineering News-Record</strong> (ENR) construction cost indexes for 55 metro areas. Labor rates reflect licensed contractor averages by trade and state. Material costs are Q2 2026 national averages with local multipliers applied.
        All estimates include ±15% variance band. DIY estimates assume handyman-level skill. Contractor estimates assume licensed, insured professionals. Emergency rates assume same-day or after-hours availability.
        </div>
    </div>
    """, unsafe_allow_html=True)

def page_depreciation():
    render_page_header("System Depreciation & 24-Month CapEx Risk Horizon", "depreciation", "Shows remaining useful life and failure probability of every major system, plus upcoming replacement costs.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_property_banner()
    render_realtime_badge("Depreciation Analysis Q2 2026")

    capex = st.session_state.capex_analysis
    horizon = st.session_state.get("capex_horizon", {})
    items = capex.get("capex_items", [])
    summary = capex.get("summary", {})

    total_systems = summary.get("total_systems_assessed", 0)
    total_replacement = summary.get("total_replacement_value", 0)
    weighted_risk = summary.get("weighted_24mo_risk", 0)
    highest_risk = summary.get("highest_risk_system", "N/A")

    critical_items = len([i for i in items if i.get("failure_probability_24mo", 0) > 70])
    at_risk = len([i for i in items if 40 < i.get("failure_probability_24mo", 0) <= 70])

    st.markdown(f"""
    <div style="background:linear-gradient(135deg, rgba(255,159,10,0.08), rgba(255,69,58,0.06));border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:1.5rem;margin-bottom:1.5rem;">
        <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#FF9F0A;margin-bottom:0.75rem;">System Health Dashboard</div>
        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:1rem;margin-bottom:1rem;">
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Systems Assessed</div>
                <div style="font-size:1.3rem;font-weight:800;color:#F5F5F7;">{total_systems}</div>
            </div>
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Total Replacement Value</div>
                <div style="font-size:1.3rem;font-weight:800;color:#F5F5F7;">${total_replacement:,.0f}</div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);">if all replaced today</div>
            </div>
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">24-Month Risk Budget</div>
                <div style="font-size:1.3rem;font-weight:800;color:#FF9F0A;">${weighted_risk:,.0f}</div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);">expected spend</div>
            </div>
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Immediate Risk</div>
                <div style="font-size:1.3rem;font-weight:800;color:{'#FF453A' if critical_items > 0 else '#30D158'};">{critical_items}</div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);">systems >70% fail risk</div>
            </div>
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Highest Risk</div>
                <div style="font-size:1.1rem;font-weight:800;color:#F5F5F7;">{highest_risk}</div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);">top priority system</div>
            </div>
        </div>
        <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:0.75rem;">
            <div style="font-size:0.65rem;font-weight:700;color:#0A84FF;margin-bottom:0.5rem;">REPLACEMENT STRATEGY</div>
            <div style="color:#CBD5E1;font-size:0.85rem;line-height:1.7;">
            {f'{critical_items} system(s) have >70% failure probability within 24 months. These are your top negotiation priorities — request credits or seller repairs before closing. Budget ${weighted_risk:,.0f} for expected 24-month repair costs.' if critical_items > 0 else
             f'No immediate failures expected. {at_risk} system(s) are in the 40-70% risk range — plan for these replacements within 3-5 years. Budget ${weighted_risk:,.0f} for weighted 24-month risk.'}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_clickable_metric_with_explanation("Systems Assessed", str(total_systems),
            "Major home systems analyzed — HVAC, roof, plumbing, electrical, appliances. Each system's age, condition, and remaining lifespan calculated.")
    with col2:
        render_clickable_metric_with_explanation("Replacement Value", f"${total_replacement:,.0f}",
            "Cost to replace ALL systems brand new at 2026 prices. Shows the scale of infrastructure investment in the home.")
    with col3:
        render_clickable_metric_with_explanation("24-Month Risk", f"${weighted_risk:,.0f}",
            "Dollar amount you should EXPECT to spend on repairs over the next 2 years, weighted by failure probability. Your 'budget for repairs' number.")
    with col4:
        render_clickable_metric_with_explanation("Highest Risk", highest_risk,
            "Single system most likely to fail soon. Prioritize this in negotiations and get a dedicated contractor estimate.")

    with st.expander("Depreciation Timeline by System", expanded=True):
        if items:
            for idx, item in enumerate(items):
                urgency = item.get("replacement_urgency", "")
                prob = item.get("failure_probability_24mo", 0)
                remaining = item.get("remaining_life", 0)
                useful_life = item.get("useful_life", 15)
                age = item.get("estimated_age", 0)
                cost = item.get("replacement_cost_avg", 0)
                bar_width = min(100, max(5, (1 - remaining / max(useful_life, 1)) * 100))
                bar_color = "#DC2626" if prob > 70 else "#EA580C" if prob > 40 else "#CA8A04" if prob > 20 else "#16A34A"

                if prob > 70:
                    risk_label = "CRITICAL"
                    risk_bg = "rgba(255,69,58,0.04)"
                elif prob > 40:
                    risk_label = "AT RISK"
                    risk_bg = "rgba(255,159,10,0.04)"
                elif prob > 20:
                    risk_label = "AGING"
                    risk_bg = "rgba(255,214,10,0.04)"
                else:
                    risk_label = "HEALTHY"
                    risk_bg = "rgba(48,209,88,0.04)"

                with st.expander(f"{'🔴' if prob > 70 else '🟠' if prob > 40 else '🟡' if prob > 20 else '🟢'} **{item.get('system', 'N/A')}** — {risk_label} | ${cost:,.0f} replacement | {prob:.0f}% fail risk", expanded=(prob > 40)):
                    st.markdown(f"**Finding:** {item.get('finding', '')[:200]}")
                    st.markdown(f"- **Age:** {age} yrs / **Useful Life:** {useful_life} yrs / **Remaining:** {remaining:.1f} yrs")
                    st.markdown(f"- **Replacement Cost (2026):** ${cost:,.0f} | **24-Month Failure Risk:** {prob:.1f}%")
                    st.markdown(f"- **Urgency:** {urgency}")

                    expl = {70: ("#FF453A", "Very likely to fail within 2 years. Budget for replacement now and make this your #1 negotiation priority. Getting a contractor estimate now will strengthen your position."), 40: ("#FF9F0A", "Aging with significant chance of failing soon. Plan for replacement within 3-5 years. Negotiate credits and set aside reserve funds."), 20: ("#FFD60A", "Getting older but still has life left. Monitor annually. Worth mentioning in negotiations but not urgent."), 0: ("#30D158", "In good shape with plenty of remaining life. Standard maintenance sufficient.")}
                    ecolor, etext = next(((c, t) for threshold, (c, t) in expl.items() if prob > threshold), expl[0])
                    st.markdown(f"""<div style="background: rgba({int(ecolor[1:3],16)},{int(ecolor[3:5],16)},{int(ecolor[5:7],16)},0.1); border-left: 3px solid {ecolor}; padding: 0.5rem 0.75rem; border-radius: 0 6px 6px 0; margin: 0.5rem 0; font-size: 0.85rem; color: #CBD5E1;"><strong>Analysis:</strong> {etext}</div>
                    <div class="cost-bar" style="margin-top: 0.5rem;"><div class="cost-bar-fill" style="width: {bar_width}%; background: {bar_color};"></div></div>
                    <div style="color: {bar_color}; font-size: 0.75rem; font-weight: 600; margin-top: 0.25rem;">Lifespan consumed: {((1 - remaining/max(useful_life,1))*100):.0f}%</div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No depreciation data available.")

    with st.expander("Failure Probability Chart", expanded=True):
        if items:
            fig = go.Figure()
            systems = [i["system"] for i in items]
            probs = [i["failure_probability_24mo"] for i in items]
            costs = [i["replacement_cost_avg"] for i in items]
            colors = ["#DC2626" if p > 70 else "#EA580C" if p > 40 else "#CA8A04" if p > 20 else "#16A34A" for p in probs]
            fig.add_trace(go.Bar(x=systems, y=probs, marker_color=colors, text=[f"{p:.0f}%" for p in probs], textposition="auto", name="Failure Prob %"))
            fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=350, margin=dict(t=30, b=30), yaxis_title="Failure Probability (%)", xaxis_title="System")
            st.plotly_chart(fig, width='stretch')
            st.markdown("""
            <div class="deep-dive-panel">
                <h5>How to Read This Chart</h5>
                <p>Each bar shows the probability that a system will fail or need replacement within the next 24 months.<br><br>
                <strong>Red (>70%):</strong> Almost certain to need replacement. This is your top negotiation priority.<br>
                <strong>Orange (40-70%):</strong> Coin-flip chance of failure. Plan for this expense.<br>
                <strong>Yellow (20-40%):</strong> Getting risky. Worth mentioning in negotiations.<br>
                <strong>Green (<20%):</strong> Should be fine for several more years.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No failure probability data available.")

    with st.expander("24-Month CapEx Timeline", expanded=True):
        if horizon.get("visual_timeline"):
            timeline_data = horizon["visual_timeline"]
            if timeline_data:
                fig = go.Figure()
                months = list(range(0, 25))
                cumulative = []
                total = 0
                for m in months:
                    events_at_month = [e for e in timeline_data if e.get("month") == m]
                    month_cost = sum(e.get("total_cost", 0) for e in events_at_month)
                    total += month_cost
                    cumulative.append(total)
                fig.add_trace(go.Scatter(x=months, y=cumulative, mode="lines+markers", fill="tozeroy",
                    line=dict(color="#3B82F6", width=3), fillcolor="rgba(59, 130, 246, 0.1)",
                    marker=dict(size=8), name="Cumulative Risk"))
                fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    height=350, margin=dict(t=30, b=30), xaxis_title="Months from Now", yaxis_title="Cumulative Replacement Cost ($)")
                st.plotly_chart(fig, width='stretch')
                st.markdown("""
                <div class="deep-dive-panel">
                    <h5>What This Timeline Shows</h5>
                    <p>This chart shows when repair expenses are statistically likely to hit you. A steep climb in the first 6 months means big expenses are imminent. A gradual slope means you have time to plan. Use this to negotiate escrow holdbacks for items likely to fail before or shortly after closing.</p>
                </div>
                """, unsafe_allow_html=True)

def page_market():
    render_page_header("Market Analysis & Negotiation Strategy", "market", "Contextualizes repairs against current market conditions and generates item-by-item negotiation tactics.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_property_banner()
    render_realtime_badge("Market Analysis Q2 2026")

    market = st.session_state.market_profile
    negotiation = st.session_state.negotiation_strategies
    zip_code = st.session_state.get("zip_code", "N/A")

    leverage_score = market.get("leverage_score", 50)
    market_type = market.get("market_type", "Balanced")
    total_findings = len(st.session_state.findings)
    total_cost = sum(item.get("total_avg", 0) for item in st.session_state.cost_matrix.get("line_items", []))
    strategies_list = negotiation.get("strategies", [])
    exec_summary = negotiation.get("executive_summary", "")

    if leverage_score > 60:
        gradient = "rgba(48,209,88,0.08)"
        accent = "#30D158"
        leverage_label = "Strong"
    elif leverage_score > 40:
        gradient = "rgba(255,159,10,0.08)"
        accent = "#FF9F0A"
        leverage_label = "Moderate"
    else:
        gradient = "rgba(255,69,58,0.08)"
        accent = "#FF453A"
        leverage_label = "Limited"

    critical_count = len([s for s in strategies_list if s.get("severity") == "CRITICAL"])
    high_count = len([s for s in strategies_list if s.get("severity") == "HIGH"])

    st.markdown(f"""
    <div style="background:linear-gradient(135deg, {gradient}, rgba(10,132,255,0.04));border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:1.5rem;margin-bottom:1.5rem;">
        <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:{accent};margin-bottom:0.75rem;">Negotiation Dashboard — ZIP {zip_code}</div>
        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:1rem;">
            <div>
                <div style="font-size:0.65rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Market Type</div>
                <div style="font-size:1.3rem;font-weight:800;color:#F5F5F7;">{market_type}</div>
                <div style="font-size:0.65rem;color:{accent};">{market.get('avg_days_on_market', 'N/A')} days on market</div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Buyer Leverage</div>
                <div style="font-size:1.3rem;font-weight:800;color:{accent};">{leverage_score}/100</div>
                <div style="font-size:0.65rem;color:rgba(245,245,247,0.4);">{leverage_label} position</div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Total Repair Costs</div>
                <div style="font-size:1.3rem;font-weight:800;color:#F5F5F7;">${total_cost:,.0f}</div>
                <div style="font-size:0.65rem;color:rgba(245,245,247,0.4);">{total_findings} findings</div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Negotiation Items</div>
                <div style="font-size:1.3rem;font-weight:800;color:#F5F5F7;">{len(strategies_list)}</div>
                <div style="font-size:0.65rem;color:#FF453A;">{critical_count} critical / {high_count} high</div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Months Supply</div>
                <div style="font-size:1.3rem;font-weight:800;color:#F5F5F7;">{market.get('months_of_supply', 'N/A')}</div>
                <div style="font-size:0.65rem;color:rgba(245,245,247,0.4);">inventory level</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        render_clickable_metric_with_explanation("Buyer Leverage", f"{leverage_score}/100",
            "0-100 score measuring your negotiating power. Higher = more leverage. Factors: market inventory, days on market, number of competing offers, seller motivation signals, seasonal demand.")
    with col2:
        render_clickable_metric_with_explanation("Months of Supply", str(market.get("months_of_supply", 0)),
            "Months of inventory remaining. Under 3 = hot seller market (limited leverage). 3-6 = balanced. Over 6 = buyer's market (strong leverage). Directly impacts how much sellers will negotiate.")
    with col3:
        yoy = market.get("yoy_price_change_pct", 0)
        trend_label = f"{'Rising' if yoy > 2 else 'Stable' if -2 <= yoy <= 2 else 'Declining'} ({yoy:+.1f}%)"
        render_clickable_metric_with_explanation("Price Trend", trend_label,
            "Direction of home prices. Declining = sellers more motivated. Rising = less leverage. Stable = use findings as negotiation leverage.")

    if exec_summary:
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:1.25rem;margin-bottom:1.5rem;">
            <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#0A84FF;margin-bottom:0.5rem;">Executive Negotiation Summary</div>
            <div style="color:#CBD5E1;font-size:0.88rem;line-height:1.7;">{exec_summary}</div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("Leverage Assessment & Market Dynamics", expanded=True):
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:1.25rem;margin-bottom:1rem;">
            <div style="color:#CBD5E1;font-size:0.88rem;line-height:1.7;">{market.get('leverage_description', 'Market analysis not available for this area.')}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:1.25rem;">
            <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#FF9F0A;margin-bottom:0.75rem;">Credit Request Strategy</div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;">
                <div style="padding:0.75rem;background:rgba(255,69,58,0.08);border:1px solid rgba(255,69,58,0.15);border-radius:8px;text-align:center;">
                    <div style="font-size:0.6rem;color:#FF453A;font-weight:700;">AGGRESSIVE</div>
                    <div style="font-size:1.1rem;font-weight:800;color:#F5F5F7;">${total_cost:,.0f}</div>
                    <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);">100% of estimated costs</div>
                    <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);margin-top:0.25rem;">Best in strong buyer markets</div>
                </div>
                <div style="padding:0.75rem;background:rgba(255,159,10,0.08);border:1px solid rgba(255,159,10,0.15);border-radius:8px;text-align:center;">
                    <div style="font-size:0.6rem;color:#FF9F0A;font-weight:700;">MODERATE</div>
                    <div style="font-size:1.1rem;font-weight:800;color:#F5F5F7;">${total_cost * 0.65:,.0f}</div>
                    <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);">65% of estimated costs</div>
                    <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);margin-top:0.25rem;">Best in balanced markets</div>
                </div>
                <div style="padding:0.75rem;background:rgba(48,209,88,0.08);border:1px solid rgba(48,209,88,0.15);border-radius:8px;text-align:center;">
                    <div style="font-size:0.6rem;color:#30D158;font-weight:700;">CONSERVATIVE</div>
                    <div style="font-size:1.1rem;font-weight:800;color:#F5F5F7;">${total_cost * 0.40:,.0f}</div>
                    <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);">40% of estimated costs</div>
                    <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);margin-top:0.25rem;">Best in hot seller markets</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if strategies_list:
        with st.expander(f"Item-by-Item Negotiation Playbook ({len(strategies_list)} strategies)", expanded=True):
            for idx, strat in enumerate(strategies_list):
                severity = strat.get("severity", "MEDIUM")
                strategy = strat.get("strategy", "N/A")
                sev_color = {"CRITICAL": "#DC2626", "HIGH": "#EA580C", "MEDIUM": "#CA8A04", "LOW": "#16A34A"}.get(severity, "#6B7280")

                action = strat.get("action", "")
                rationale = strat.get("rationale", "")
                description = strat.get("description", "")

                if "CREDIT" in strategy.upper():
                    approach_label = "CASH CREDIT"
                    approach_desc = "Request a cash credit at closing for this repair. The seller gives you money instead of fixing it themselves. You control repair quality and timing."
                elif "FIX" in strategy.upper() or "REPAIR" in strategy.upper():
                    approach_label = "SELLER REPAIR"
                    approach_desc = "Require the seller to complete this repair before closing. Best for safety issues where you don't want to move in until fixed."
                elif "BUNDLE" in strategy.upper() or "PRICE" in strategy.upper():
                    approach_label = "PRICE REDUCTION"
                    approach_desc = "Negotiate a lower purchase price. This reduces your mortgage payment and property taxes permanently — often more valuable than a one-time credit."
                elif "LEVERAGE" in strategy.upper():
                    approach_label = "BARGAINING CHIP"
                    approach_desc = "Use this finding to strengthen your overall position. Mention it but don't demand a specific remedy."
                elif "WAIVE" in strategy.upper() or "GOODWILL" in strategy.upper():
                    approach_label = "GOODWILL TRADE"
                    approach_desc = "Consider waiving this item to build goodwill with the seller. Small cosmetic issues can be traded for concessions on bigger items."
                else:
                    approach_label = strategy.split(":")[0] if ":" in strategy else "CUSTOM"
                    approach_desc = strategy

                st.markdown(f"""<div style="padding:1rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;margin-bottom:0.75rem;">
                    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
                        <span style="background:{sev_color};color:white;padding:0.15rem 0.5rem;border-radius:999px;font-size:0.65rem;font-weight:700;">{severity}</span>
                        <span style="color:#F5F5F7;font-weight:700;font-size:0.85rem;">{strat.get('system', 'N/A')}</span>
                        <span style="color:rgba(245,245,247,0.4);font-size:0.75rem;">—</span>
                        <span style="color:#CBD5E1;font-size:0.8rem;">{description[:80] if description else 'N/A'}</span>
                    </div>
                    <div style="padding:0.5rem 0.75rem;background:rgba(10,132,255,0.06);border-left:3px solid #0A84FF;border-radius:0 6px 6px 0;margin-bottom:0.5rem;">
                        <div style="font-size:0.7rem;font-weight:700;color:#0A84FF;">{approach_label}</div>
                        <div style="color:#CBD5E1;font-size:0.8rem;line-height:1.6;">{approach_desc}</div>
                    </div>
                    <div style="color:#CBD5E1;font-size:0.8rem;line-height:1.6;margin-bottom:0.5rem;">
                        <strong style="color:#F5F5F7;">Action:</strong> {action}
                    </div>
                    <div style="color:#CBD5E1;font-size:0.8rem;line-height:1.6;">
                        <strong style="color:#F5F5F7;">Why this works:</strong> {rationale}
                    </div>
                </div>""", unsafe_allow_html=True)

    with st.expander("Market Trends & Context"):
        yoy = market.get("yoy_price_change_pct", 0)
        abs_rate = market.get("absorption_rate", 0)
        st.markdown(f"""
        <div style="padding:1rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;margin-bottom:1rem;">
            <div style="font-size:0.7rem;font-weight:700;color:#0A84FF;margin-bottom:0.5rem;">MARKET CONTEXT</div>
            <div style="color:#CBD5E1;font-size:0.85rem;line-height:1.7;">
            {market.get('leverage_description', 'Market analysis not available for this area.')}<br><br>
            <strong style="color:#F5F5F7;">Current timing advice:</strong> {'This is a strong seller market. Be strategic — focus only on critical safety items in your negotiation. Avoid including cosmetic or low-priority items as it risks losing the deal.' if leverage_score < 30 else 'Market is balanced. You have reasonable leverage to negotiate on all severity levels. Bundle medium items with critical/high items for maximum impact.' if leverage_score < 60 else 'This is a buyer-favorable market. Sellers are motivated and have longer days on market. Push for comprehensive credits covering all findings — the seller has limited alternatives.'}
            </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;">
            <div style="padding:0.75rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;">
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);text-transform:uppercase;">Price Change (YoY)</div>
                <div style="font-size:0.9rem;font-weight:700;color:{'#30D158' if yoy > 0 else '#FF453A'};">{yoy:+.1f}%</div>
            </div>
            <div style="padding:0.75rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;">
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);text-transform:uppercase;">Absorption Rate</div>
                <div style="font-size:0.9rem;font-weight:700;color:#F5F5F7;">{abs_rate:.1f}%</div>
            </div>
            <div style="padding:0.75rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;">
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);text-transform:uppercase;">Active Listings</div>
                <div style="font-size:0.9rem;font-weight:700;color:#F5F5F7;">{market.get('active_listings', 0):,}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="callout-warning" style="padding: 0.75rem 1rem; border-radius: 8px; margin-top: 1rem;">
        <div style="font-weight: 700; color: #FCD34D; margin-bottom: 0.3rem; font-size: 0.8rem;">When to Walk Away</div>
        <div style="color: #CBD5E1; font-size: 0.78rem; line-height: 1.6;">
        Consider walking away if: (1) Seller refuses to address ANY safety issues (CRITICAL findings), (2) Total estimated repairs exceed 10% of purchase price, (3) You discover intentional concealment or misrepresentation, (4) Repair costs exceed what you could recoup in resale value, (5) The home has environmental hazards (asbestos, lead, radon above 4.0 pCi/L) that are prohibitively expensive to remediate.
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_disclaimer(MARKET_DATA_NOTE)

def page_contractor_bids():
    render_page_header("Contractor Bid & Dispatch Engine", "contractor_bids", "Simulates receiving multiple contractor bids for each finding with recommended contractors.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_property_banner()
    render_realtime_badge("Contractor Bids 2026")

    bids_data = st.session_state.contractor_bids
    summary = bids_data.get("summary", {})
    by_finding = bids_data.get("by_finding", {})

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_clickable_metric_with_explanation("Total Bids", str(summary.get("total_bids_received", 0)),
            "This is how many individual contractor bids were received across all findings. More bids give you better price comparison and negotiation leverage.")
    with col2:
        render_clickable_metric_with_explanation("Findings with Bids", str(summary.get("total_findings_with_bids", 0)),
            "The number of inspection findings that received contractor bids. Some minor items may not need separate bids.")
    with col3:
        render_clickable_metric_with_explanation("Lowest Total", f"${summary.get('lowest_total', 0):,.0f}",
            "The total cost if you hire the cheapest contractor for every item. Be careful — cheapest isn't always best. Check ratings and warranties.")
    with col4:
        render_clickable_metric_with_explanation("Potential Savings", f"${summary.get('potential_savings_range', 0):,.0f}",
            "The difference between highest and lowest bids. This is your negotiation range — you can save this much by choosing wisely.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    breakdown = bids_data.get("cost_breakdown_summary", {})
    if breakdown:
        with st.expander("Cost Breakdown Summary", expanded=True):
            bc1, bc2, bc3, bc4, bc5 = st.columns(5)
            with bc1:
                st.metric("Materials", f"${breakdown.get('total_material', 0):,.0f}", f"{breakdown.get('material_pct', 0):.0f}% of total")
            with bc2:
                st.metric("Labor", f"${breakdown.get('total_labor', 0):,.0f}", f"{breakdown.get('labor_pct', 0):.0f}% of total")
            with bc3:
                st.metric("Overhead", f"${breakdown.get('total_overhead', 0):,.0f}", f"{breakdown.get('overhead_pct', 0):.0f}% of total")
            with bc4:
                st.metric("Profit", f"${breakdown.get('total_profit', 0):,.0f}", f"{breakdown.get('profit_pct', 0):.0f}% of total")
            with bc5:
                st.metric("Permits", f"${breakdown.get('total_permits', 0):,.0f}", "Required for CRITICAL/HIGH")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    recommendations = get_contractor_recommendations(by_finding)
    with st.expander("Recommended Contractors (Top Priority)", expanded=True):
        if recommendations:
            for rec in recommendations:
                with st.expander(f"**{rec['recommended_contractor']}** | {rec['system']} | ${rec['bid_amount']:,.0f}", expanded=False):
                    st.markdown(f"**Finding:** {rec['finding']}")
                    st.markdown(f"- **Contractor:** {rec['recommended_contractor']} ({rec.get('years_experience', 'N/A')} years experience)")
                    st.markdown(f"- **Rating:** {rec['rating']}/5.0 stars")
                    st.markdown(f"- **Warranty:** {rec['warranty']}")
                    st.markdown(f"- **Timeline:** {rec['timeline']}")
                    st.markdown(f"- **Bid Amount:** ${rec['bid_amount']:,.0f}")
                    st.markdown(f"- **Material Cost:** ${rec.get('material_breakdown', 0):,.0f}")
                    st.markdown(f"- **Labor Cost:** ${rec.get('labor_breakdown', 0):,.0f}")
                    st.markdown(f"- **Savings vs Average:** ${rec['savings_vs_avg']:,.0f}")
                    st.markdown("---")
                    st.info(f"**Why this contractor:** They offer the best combination of low price, good rating ({rec['rating']}/5.0), and solid warranty ({rec['warranty']}). They can complete the work in {rec['timeline']}.")
        else:
            st.info("No contractor recommendations available.")

    with st.expander("All Bids by Finding", expanded=False):
        for fid, data in by_finding.items():
            bids = data.get("bids", [])
            st.markdown(f"**{data.get('system', 'N/A')}** — {data.get('finding', '')[:80]}")
            if data.get("bid_spread_pct", 0) > 0:
                st.caption(f"Bid spread: {data['bid_spread_pct']:.1f}% — potential savings: ${data.get('savings_vs_highest', 0):,.0f}")
            for bid in sorted(bids, key=lambda x: x.get("bid_amount", 0)):
                tag = ""
                if bid.get("is_lowest"):
                    tag = " LOWEST"
                elif bid.get("is_highest"):
                    tag = " HIGHEST"
                with st.expander(f"{bid.get('contractor_name', 'N/A')}{tag} — ${bid.get('bid_amount', 0):,.0f}", expanded=False):
                    st.markdown(f"- **Rating:** {bid.get('contractor_rating', 0)}/5.0 ({bid.get('contractor_years', 'N/A')} years)")
                    st.markdown(f"- **Specialty:** {bid.get('contractor_specialty', 'General')}")
                    st.markdown(f"- **Warranty:** {bid.get('warranty_terms', '')}")
                    st.markdown(f"- **Timeline:** {bid.get('timeline_days', 0)} days")
                    st.markdown(f"- **Payment Terms:** {bid.get('payment_terms', 'Net 30')}")
                    st.markdown(f"- **Insurance Verified:** {'Yes' if bid.get('insurance_verified') else 'No'}")
                    st.markdown(f"- **License Verified:** {'Yes' if bid.get('license_verified') else 'No'}")
                    st.markdown(f"- **Material Cost:** ${bid.get('material_cost', 0):,.0f}")
                    st.markdown(f"- **Labor Cost:** ${bid.get('labor_cost', 0):,.0f} ({bid.get('labor_hours', 0)} hours)")
                    st.markdown(f"- **Overhead:** ${bid.get('overhead_cost', 0):,.0f}")
                    st.markdown(f"- **Profit Margin:** ${bid.get('profit_margin', 0):,.0f}")
                    if bid.get("permit_cost", 0) > 0:
                        st.markdown(f"- **Permit Cost:** ${bid.get('permit_cost', 0):,.0f}")
                    if bid.get("rush_cost"):
                        st.markdown(f"- **Rush/After-Hours:** ${bid['rush_cost']:,.0f} ({bid.get('rush_timeline', 'N/A')} days)")
                    if bid.get("is_lowest"):
                        st.success("This is the lowest bid. Best value if their quality and warranty are acceptable.")
                    elif bid.get("is_highest"):
                        st.warning("This is the highest bid. They may offer premium quality, but compare carefully.")

def page_sandbox():
    render_page_header("Interactive Seller Credit Sandbox", "sandbox", "Check/uncheck items, change repair types, and override amounts. Total updates in real-time.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_realtime_badge("Live Sandbox")

    findings = st.session_state.findings
    cost_matrix = st.session_state.cost_matrix
    market = st.session_state.market_profile

    if not st.session_state.sandbox_items:
        session = create_sandbox_session(st.session_state.property_data, findings, cost_matrix)
        st.session_state.sandbox_items = session["items"]

    items = st.session_state.sandbox_items
    totals = calculate_sandbox_totals(items, market)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(render_metric_card("Items Selected", f"{totals['selected_items']} / {totals['total_items']}"), unsafe_allow_html=True)
    with col2:
        st.markdown(render_metric_card("Total Requested", f"${totals['total_requested']:,.0f}"), unsafe_allow_html=True)
    with col3:
        st.markdown(render_metric_card("Expected Concession", f"${totals['expected_concession']:,.0f}"), unsafe_allow_html=True)
    with col4:
        st.markdown(render_metric_card("Acceptance Rate", f"{totals['expected_concession_pct']:.0f}%"), unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    for idx, item in enumerate(items):
        severity = item.get("severity", "MEDIUM")
        sev_color = {"CRITICAL": "#DC2626", "HIGH": "#EA580C", "MEDIUM": "#CA8A04", "LOW": "#16A34A"}.get(severity, "#6B7280")
        st.markdown(f"""
        <div class="sandbox-item" style="border-left: 4px solid {sev_color};">
            <div style="flex: 1;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    {render_severity_badge(severity)}
                    <span style="font-weight: 600; color: #F1F5F9; font-size: 0.9rem;">{item.get('system', 'N/A')}</span>
                </div>
                <div style="color: #94A3B8; font-size: 0.8rem;">{item.get('description', '')[:100]}</div>
                <div style="color: #64748B; font-size: 0.75rem;">Est: ${item.get('estimated_cost', 0):,.0f} | Range: ${item.get('estimated_low', 0):,.0f} - ${item.get('estimated_high', 0):,.0f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            new_selected = st.checkbox("Include", value=item.get("selected", False), key=f"sandbox_sel_{idx}")
        with col2:
            repair_type = st.selectbox("Type", ["seller_credit", "seller_repair", "price_reduction", "waived"], index=["seller_credit", "seller_repair", "price_reduction", "waived"].index(item.get("repair_type", "seller_credit")), key=f"sandbox_type_{idx}")
        with col3:
            override = st.number_input("Override $", value=float(item.get("override_amount") or item.get("estimated_cost", 0)), key=f"sandbox_override_{idx}")

        if new_selected != item.get("selected") or repair_type != item.get("repair_type") or override != item.get("override_amount"):
            update_item_selection(items, idx, new_selected, repair_type, override)
            st.session_state.sandbox_items = items

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="sandbox-total">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-size: 0.85rem; opacity: 0.8;">TOTAL SELLER CONCESSION REQUEST</div>
                <div class="total-value">${totals['total_requested']:,.0f}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.85rem; opacity: 0.8;">EXPECTED CONCESSION</div>
                <div style="font-size: 2rem; font-weight: 800;">${totals['expected_concession']:,.0f}</div>
                <div style="font-size: 0.85rem; opacity: 0.8;">({totals['expected_concession_pct']:.0f}% acceptance rate)</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def page_legal():
    render_page_header("Automated Legal Addendum & Repair Request Writer", "legal", "Auto-generates a professional Repair Request Addendum using standard real estate contractual language.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_realtime_badge("Legal Document Generator")

    findings = st.session_state.findings
    cost_matrix = st.session_state.cost_matrix
    high_risk_findings = [f for f in findings if f.get("severity") in ["CRITICAL", "HIGH"]]

    st.markdown(f"**{len(high_risk_findings)}** high-priority items ready for legal addendum generation")
    addendum = generate_legal_addendum(st.session_state.property_data, findings, cost_matrix, high_risk_findings)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(render_metric_card("Repair Items", str(addendum.get("total_repair_items", 0))), unsafe_allow_html=True)
    with col2:
        st.markdown(render_metric_card("Credit Items", str(addendum.get("total_credit_items", 0))), unsafe_allow_html=True)
    with col3:
        st.markdown(render_metric_card("Total Value", f"${addendum.get('total_requested_value', 0):,.0f}"), unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    with st.expander("Generated Legal Addendum", expanded=True):
        addendum_text = addendum.get("addendum_text", "")
        st.markdown(f"""
        <div class="legal-addendum">
            <pre style="white-space: pre-wrap; font-family: 'Times New Roman', serif; color: #1a1a1a; font-size: 0.95rem;">{addendum_text}</pre>
        </div>
        """, unsafe_allow_html=True)

    st.download_button("Download Legal Addendum", addendum_text, file_name="repair_request_addendum.txt", mime="text/plain")

    render_disclaimer(HELP_CONTENT.get("legal", {}).get("sections", {}).get("Disclaimer", ""))

def page_insurance():
    render_page_header("Home Insurance P&C Premium Risk Predictor", "insurance", "Scans findings for insurance red flags - issues that cause carriers to deny coverage or raise premiums.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_property_banner()
    render_realtime_badge("Insurance Risk Q2 2026")

    insurance = st.session_state.insurance_analysis
    summary = insurance.get("summary", {})
    red_flags = insurance.get("red_flags", [])

    score = summary.get("insurability_score", 50)
    grade = "A" if score >= 90 else "B+" if score >= 80 else "B" if score >= 70 else "C+" if score >= 60 else "C" if score >= 50 else "D" if score >= 40 else "F"
    grade_color = "#10B981" if score >= 70 else "#F59E0B" if score >= 50 else "#EF4444"

    annual_impact = summary.get("total_annual_premium_impact", 0)
    five_yr_impact = summary.get("five_year_cost_impact", 0)
    total_flags = summary.get("total_red_flags", 0)
    replacement_total = sum(f.get("replacement_cost", 0) for f in red_flags)

    st.markdown(f"""
    <div style="background:linear-gradient(135deg, rgba(139,92,246,0.08), rgba(10,132,255,0.06));border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:1.5rem;margin-bottom:1.5rem;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">
            <div>
                <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#8B5CF6;margin-bottom:0.25rem;">Insurance Risk Dashboard</div>
                <div style="font-size:1.5rem;font-weight:800;color:#F5F5F7;">Grade: {grade} — {'Standard Coverage Expected' if score >= 80 else 'May Face Coverage Challenges' if score >= 60 else 'Significant Coverage Risks Identified' if score >= 40 else 'Coverage May Be Denied'}</div>
            </div>
            <div style="text-align:center;padding:0.75rem 1.5rem;background:rgba(255,255,255,0.05);border-radius:12px;border:2px solid {grade_color};">
                <div style="font-size:2.5rem;font-weight:800;color:{grade_color};">{score}</div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);">out of 100</div>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;">
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Red Flags</div>
                <div style="font-size:1.3rem;font-weight:800;color:{'#FF453A' if total_flags > 3 else '#FF9F0A' if total_flags > 0 else '#30D158'};">{total_flags}</div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);">carrier concerns</div>
            </div>
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Annual Premium Impact</div>
                <div style="font-size:1.3rem;font-weight:800;color:#FF9F0A;">${annual_impact:,.0f}/yr</div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);">additional cost</div>
            </div>
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">5-Year Cost</div>
                <div style="font-size:1.3rem;font-weight:800;color:#FF453A;">${five_yr_impact:,.0f}</div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);">cumulative impact</div>
            </div>
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Remediation Cost</div>
                <div style="font-size:1.3rem;font-weight:800;color:#F5F5F7;">${replacement_total:,.0f}</div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);">to fix all flags</div>
            </div>
        </div>
        <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:0.75rem;margin-top:0.75rem;">
            <div style="font-size:0.65rem;font-weight:700;color:#8B5CF6;margin-bottom:0.5rem;">COVERAGE IMPACT SUMMARY</div>
            <div style="color:#CBD5E1;font-size:0.85rem;line-height:1.7;">
            {'No significant insurance concerns. Standard homeowner policies should be available at competitive rates.' if score >= 80 else
             'Some carriers may exclude specific claims or require additional inspections. Shop multiple carriers for best rates.' if score >= 60 else
             'Significant challenges expected. Many carriers may decline. Consider resolving red flags BEFORE closing to reduce long-term costs.' if score >= 40 else
             'Standard carriers may refuse coverage entirely. High-risk specialty carriers only — expect 2-3x normal premiums. Resolve critical flags before closing.'}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_clickable_metric_with_explanation("Insurability Score", f"{score}/100 ({grade})",
            f"Letter grade for insurability. A = standard rates. F = carriers may refuse coverage. Your {score} ({grade}) means {'easily insurable' if score >= 70 else 'may face challenges'}.")
    with col2:
        render_clickable_metric_with_explanation("Red Flags", str(total_flags),
            "Issues insurance companies specifically look for — polybutylene plumbing, knob-and-tube wiring, active mold, aluminum wiring. Each causes denials, exclusions, or higher premiums.")
    with col3:
        render_clickable_metric_with_explanation("Annual Premium Impact", f"${annual_impact:,.0f}/yr",
            "Extra yearly insurance cost. $3,000/yr impact on $2,000 base premium = $5,000 total per year. Over 10 years, that's $30,000 extra.")
    with col4:
        render_clickable_metric_with_explanation("5-Year Cost Impact", f"${five_yr_impact:,.0f}",
            "Total extra insurance cost over 5 years. This is real money — factor it into your total cost of ownership alongside mortgage, taxes, and maintenance.")

    with st.expander("Insurance Red Flags Detail", expanded=True):
        if red_flags:
            for idx, flag in enumerate(red_flags):
                risk_score = flag.get("risk_score", 0)
                severity = flag.get("severity", "MEDIUM")
                denial_prob = flag.get("denial_probability", 0) * 100
                annual_cost = flag.get("annual_premium_impact", 0)
                replacement_cost = flag.get("replacement_cost", 0)

                if risk_score >= 90:
                    risk_bg = "rgba(255,69,58,0.06)"
                    risk_border = "#FF453A"
                    risk_icon = "CRITICAL"
                elif risk_score >= 80:
                    risk_bg = "rgba(255,159,10,0.06)"
                    risk_border = "#FF9F0A"
                    risk_icon = "HIGH"
                else:
                    risk_bg = "rgba(255,214,10,0.06)"
                    risk_border = "#FFD60A"
                    risk_icon = "MODERATE"

                st.markdown(f"""<div style="padding:1rem;background:{risk_bg};border:1px solid {risk_border}20;border-left:3px solid {risk_border};border-radius:10px;margin-bottom:0.75rem;">
                    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
                        <span style="background:{risk_border};color:white;padding:0.15rem 0.5rem;border-radius:999px;font-size:0.6rem;font-weight:700;">{risk_icon}</span>
                        <span style="color:#F5F5F7;font-weight:700;font-size:0.85rem;">{flag.get('red_flag_type', 'N/A')}</span>
                        <span style="color:rgba(245,245,247,0.3);font-size:0.75rem;">|</span>
                        <span style="color:#CBD5E1;font-size:0.8rem;">{flag.get('system', 'N/A')}</span>
                    </div>
                    <div style="color:#CBD5E1;font-size:0.82rem;line-height:1.6;margin-bottom:0.5rem;">{flag.get('description', 'N/A')}</div>
                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.5rem;margin-bottom:0.5rem;">
                        <div style="padding:0.4rem;background:rgba(0,0,0,0.2);border-radius:6px;text-align:center;">
                            <div style="font-size:0.55rem;color:rgba(245,245,247,0.4);">DENIAL RISK</div>
                            <div style="font-size:0.85rem;font-weight:700;color:{'#FF453A' if denial_prob > 60 else '#FF9F0A' if denial_prob > 30 else '#FFD60A'};">{denial_prob:.0f}%</div>
                        </div>
                        <div style="padding:0.4rem;background:rgba(0,0,0,0.2);border-radius:6px;text-align:center;">
                            <div style="font-size:0.55rem;color:rgba(245,245,247,0.4);">EXTRA PREMIUM</div>
                            <div style="font-size:0.85rem;font-weight:700;color:#FF9F0A;">${annual_cost:,.0f}/yr</div>
                        </div>
                        <div style="padding:0.4rem;background:rgba(0,0,0,0.2);border-radius:6px;text-align:center;">
                            <div style="font-size:0.55rem;color:rgba(245,245,247,0.4);">TO FIX</div>
                            <div style="font-size:0.85rem;font-weight:700;color:#F5F5F7;">${replacement_cost:,.0f}</div>
                        </div>
                    </div>
                    <div style="padding:0.5rem 0.75rem;background:rgba(10,132,255,0.06);border-radius:6px;">
                        <div style="font-size:0.75rem;color:#CBD5E1;line-height:1.6;"><strong style="color:#F5F5F7;">Recommendation:</strong> {flag.get('recommendation', 'Address this issue.')}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.success("No insurance red flags identified. Property appears fully insurable at standard rates.")

    if red_flags:
        with st.expander("Insurance Shopping Guide"):
            total_fix_cost = sum(f.get("replacement_cost", 0) for f in red_flags)
            roi_years = total_fix_cost / max(annual_impact, 1)
            st.markdown(f"""<div style="padding:1rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;">
                <div style="font-size:0.7rem;font-weight:700;color:#8B5CF6;margin-bottom:0.5rem;">SHOULD YOU FIX BEFORE OR AFTER PURCHASE?</div>
                <div style="color:#CBD5E1;font-size:0.85rem;line-height:1.7;">
                <strong style="color:#F5F5F7;">Total remediation cost:</strong> ${total_fix_cost:,.0f}<br>
                <strong style="color:#F5F5F7;">Annual insurance savings if fixed:</strong> ${annual_impact:,.0f}/yr<br>
                <strong style="color:#F5F5F7;">Payback period:</strong> {roi_years:.1f} years<br><br>
                {f'Fix before purchase — payback is under 3 years. You will save money overall.' if roi_years < 3 else
                 f'Consider negotiating a credit for remediation cost — payback is {roi_years:.1f} years.' if roi_years < 5 else
                 f'Remediation may not be cost-effective purely from insurance savings. Factor in resale value and safety benefits.'}
                </div>
            </div>""", unsafe_allow_html=True)

    render_disclaimer("Insurance risk scores are estimated based on industry-standard underwriting criteria and inspection pattern matching. Actual underwriting decisions are made by licensed insurance carriers. Always consult with a licensed insurance agent for coverage decisions.")

def page_environmental():
    render_page_header("Environmental Risk & Climate Resiliency Assessment", "environmental", "Cross-references location against FEMA flood zones, seismic zones, wildfire risk, and climate hazards.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_property_banner()
    render_realtime_badge("Environmental Risk 2026")

    env = st.session_state.environmental_data
    summary = env.get("summary", {})

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_clickable_metric_with_explanation("Overall Risk", summary.get("overall_risk_level", "N/A"),
            "This rates the total environmental risk for the property based on its location. HIGH means multiple serious climate/natural hazards. MEDIUM means some notable risks. LOW means relatively safe from environmental threats.")
    with col2:
        render_clickable_metric_with_explanation("Climate Zone", summary.get("climate_zone", "N/A"),
            "This identifies the property's climate zone which determines what weather-related risks are most relevant. For example, hot-humid zones have mold/termite/hurricane risk while cold-harsh zones have ice dam/frozen pipe risk.")
    with col3:
        render_clickable_metric_with_explanation("Flood Zone", summary.get("flood_zone", "N/A"),
            "This is the FEMA flood zone designation. Zone X means minimal flood risk. Zone AE or A means HIGH flood risk — flood insurance is typically REQUIRED by lenders. This significantly impacts your insurance costs and property value.")
    with col4:
        render_clickable_metric_with_explanation("Total Risks", str(summary.get("total_risks_identified", 0)),
            "The number of distinct environmental risks identified for this property's location. Each risk has its own score, insurance impact, and mitigation recommendations.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    detailed_profiles = env.get("detailed_profiles", {})
    if detailed_profiles:
        with st.expander("Detailed Environmental Profiles", expanded=False):
            for profile_type, profile_data in detailed_profiles.items():
                if profile_data:
                    st.markdown(f"**{profile_type.upper()} Profile:**")
                    for key, value in profile_data.items():
                        if isinstance(value, str) and len(value) > 10:
                            st.markdown(f"- **{key.replace('_', ' ').title()}:** {value}")
                    st.markdown("---")

    for idx, risk in enumerate(env.get("risks", [])):
        risk_level = risk.get("risk_level", "LOW")
        risk_color = {"HIGH": "#DC2626", "MEDIUM": "#CA8A04", "LOW": "#16A34A"}.get(risk_level, "#6B7280")
        with st.expander(f"{'🔴' if risk_level == 'HIGH' else '🟡' if risk_level == 'MEDIUM' else '🟢'} **{risk.get('risk_type', 'N/A')}** — Risk Level: {risk_level} (Score: {risk.get('risk_score', 0)}/100)", expanded=(risk_level == "HIGH")):
            st.markdown(f"**What this risk is:** {risk.get('description', 'N/A')}")
            st.markdown(f"- **Risk Score:** {risk.get('risk_score', 0)}/100")
            st.markdown(f"- **Annual Insurance Impact:** ${risk.get('insurance_impact', 0):,.0f}/year")
            st.markdown(f"- **Estimated Mitigation Cost:** ${risk.get('estimated_cost', 0):,.0f}")
            if risk.get("source"):
                st.markdown(f"- **Data Source:** {risk['source']}")
            if risk.get("mandatory_insurance"):
                st.markdown(f"- **Mandatory Flood Insurance:** Yes — required for federally-backed mortgages")
            if risk.get("annual_risk_pct"):
                st.markdown(f"- **Annual Risk Probability:** {risk['annual_risk_pct']}%")
            if risk.get("pga_value"):
                st.markdown(f"- **Peak Ground Acceleration:** {risk['pga_value']}")
            st.markdown(f"**How to protect against this:** {risk.get('mitigation_recommendation', 'N/A')}")
            st.markdown("---")
            if risk_level == "HIGH":
                st.error("**This is a serious environmental risk.** It can affect your insurance rates, property value, and safety. Discuss with your insurance agent and consider mitigation before closing.")
            elif risk_level == "MEDIUM":
                st.warning("**This is a notable environmental risk.** Factor it into your total cost of ownership and consider mitigation measures.")
            else:
                st.success("**This is a minor environmental concern.** Standard precautions are sufficient.")

def page_permits():
    render_page_header("Permit & Public Records Cross-Reference", "permits", "Simulates checking municipal permit records and cross-references them against inspection findings.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_property_banner()
    render_realtime_badge("Permit Records")

    permit_data = st.session_state.permit_data
    permit_raw = st.session_state.permit_raw

    col1, col2, col3 = st.columns(3)
    with col1:
        render_clickable_metric_with_explanation("Permits Found", str(permit_raw.get("total_permits", 0)),
            "The number of permit records found for this property in the simulated municipal database. These are building, electrical, plumbing, or mechanical permits on file.")
    with col2:
        render_clickable_metric_with_explanation("Unpermitted Flags", str(permit_data.get("unpermitted_flags", 0)),
            "Findings where NO matching permit was found. This means work may have been done without proper permits — a potential legal and liability issue that could affect insurance coverage and resale value.")
    with col3:
        status = permit_data.get("overall_compliance_status", "CLEAR")
        render_clickable_metric_with_explanation("Compliance Status", status,
            "CLEAR means all major work appears to have proper permits. FLAGS means some work may be unpermitted. This is based on matching findings to available permits.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    if permit_data.get("unpermitted_flags", 0) > 0:
        st.markdown("### Unpermitted Work Warnings")
        for warning in permit_data.get("unpermitted_warnings", []):
            with st.expander(f"⚠️ **{warning.get('system', 'N/A')}** — POTENTIALLY UNPERMITTED", expanded=True):
                st.markdown(f"**What this means:** {warning.get('warning', '')}")
                st.markdown(f"**Potential liability range:** {warning.get('potential_liability_range', 'N/A')}")
                st.error("**This is important:** Unpermitted work can cause problems when you sell the home, may not be covered by insurance, and could require expensive retroactive permits or even removal and redo of the work. Discuss with your real estate attorney.")

    st.markdown("### Municipal Permit Records")
    for permit in permit_raw.get("permits_found", []):
        status = permit.get("status", "Unknown")
        with st.expander(f"{'✅' if status == 'Closed' else '⏳' if status == 'Pending' else '❌'} **{permit.get('permit_type', 'N/A')}** — Status: {status}", expanded=False):
            st.markdown(f"- **Description:** {permit.get('description', 'N/A')}")
            st.markdown(f"- **Permit #:** {permit.get('permit_number', 'N/A')}")
            st.markdown(f"- **Date:** {permit.get('permit_date', 'N/A')}")
            st.markdown(f"- **Contractor:** {permit.get('contractor', 'N/A')}")
            st.markdown("---")
            if status == "Closed":
                st.success("This permit is closed/completed — the work was inspected and approved.")
            elif status == "Pending":
                st.warning("This permit is still open/pending — work may be in progress or inspection not yet completed.")
            else:
                st.info(f"Status: {status}")

def page_recalls():
    render_page_header("Manufacturer Recall Cross-Reference", "recalls", "Checks findings against known recalls and class action settlements. A defect might be a free recall repair.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_realtime_badge("Recall Database 2026")

    recalls = st.session_state.recall_data
    summary = recalls.get("summary", {})

    col1, col2, col3 = st.columns(3)
    with col1:
        render_clickable_metric_with_explanation("Recalls Checked", str(summary.get("total_recalls_checked", 0)),
            "The number of known manufacturer recalls and class action settlements that were checked against your findings. This database covers major home system manufacturers.")
    with col2:
        render_clickable_metric_with_explanation("Matches Found", str(summary.get("matches_found", 0)),
            "The number of findings that matched a known recall or defect. A match means the issue in your home may qualify for a FREE repair or replacement under a recall program.")
    with col3:
        render_clickable_metric_with_explanation("Potential Savings", f"${summary.get('total_potential_savings', 0):,.0f}",
            "The total estimated cost savings if all recall-matched items qualify for free repair/replacement. This is money you might not have to spend if you file recall claims.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    for result in recalls.get("recall_results", []):
        status = result.get("recall_status", "Check")
        with st.expander(f"{'🔴' if status == 'Active' else '🟡'} **{result.get('manufacturer', 'N/A')}** — {result.get('product_type', 'N/A')} | Status: {status}", expanded=(status == "Active")):
            st.markdown(f"**What this recall is:** {result.get('description', 'N/A')}")
            st.markdown(f"- **Manufacturer:** {result.get('manufacturer', 'N/A')}")
            st.markdown(f"- **Product:** {result.get('product_type', 'N/A')}")
            st.markdown(f"- **Recall Status:** {status}")
            st.markdown(f"- **Remedy:** {result.get('remedy', 'N/A')}")
            st.markdown(f"- **Action Required:** {result.get('action_required', 'N/A')}")
            st.markdown(f"- **Potential Savings:** ${result.get('cost_savings', 0):,.0f}")
            st.markdown("---")
            if status == "Active":
                st.error(f"**This is an ACTIVE recall.** {result.get('remedy', 'Contact the manufacturer immediately.')} You may qualify for a FREE repair. File a claim as soon as possible.")
            else:
                st.warning(f"**This may be a recall match.** {result.get('action_required', 'Check with the manufacturer.')} Even if the recall is older, you may still qualify for remedies.")

def page_photos():
    render_page_header("Photo Evidence & Visual Documentation", "photos", "Extracts photos from the original PDF and matches them to specific findings.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_realtime_badge("Photo Evidence")

    photo_analysis = st.session_state.get("photo_analysis", None)
    if photo_analysis:
        matched = photo_analysis.get("matched_photos", {})
        unmatched = photo_analysis.get("unmatched_images", [])
        summary = photo_analysis.get("summary", {})

        col1, col2, col3 = st.columns(3)
        with col1:
            render_clickable_metric_with_explanation("Total Images", str(summary.get("total_images_extracted", 0)),
                "Total number of images found in the PDF inspection report.")
        with col2:
            render_clickable_metric_with_explanation("Matched to Findings", str(summary.get("matched_to_findings", 0)),
                "Images that were successfully matched to specific inspection findings based on page proximity and keywords.")
        with col3:
            render_clickable_metric_with_explanation("Match Rate", f"{summary.get('match_rate', 0):.0f}%",
                "Percentage of images that were matched. Higher is better — it means the inspection report had clear photo-to-finding associations.")

        if matched:
            st.markdown("### Matched Photos")
            for finding_key, photos in matched.items():
                with st.expander(f"📷 {finding_key}", expanded=False):
                    for photo in photos:
                        st.markdown(f"- **Image {photo.get('image_index', 'N/A')}:** Page {photo.get('page_number', 'N/A')} | Size: {photo.get('width', 0)}x{photo.get('height', 0)}px | Type: {photo.get('image_type', 'N/A')}")
                    st.info("In production, the actual extracted images would be displayed here alongside their matched finding details.")
        if unmatched:
            with st.expander(f"Unmatched Images ({len(unmatched)})", expanded=False):
                for img in unmatched:
                    st.markdown(f"- Image {img.get('image_index', 'N/A')} on page {img.get('page_number', 'N/A')}: {img.get('reason', 'No matching finding found')}")
    else:
        st.info("Photo evidence extraction requires the original PDF. Upload a report to extract and match photos with findings.")
        st.markdown("""
        <div class="callout-info" style="padding: 1.25rem; border-radius: 10px;">
            <div style="font-weight: 700; color: #93C5FD; margin-bottom: 0.5rem;">How Photo Evidence Matching Works</div>
            <div style="color: #CBD5E1; font-size: 0.85rem;">
            1. Extracts all images from the PDF using PyMuPDF layout analysis<br>
            2. Maps text coordinates to image blocks using spatial proximity<br>
            3. Matches photos to findings using keyword overlap and context<br>
            4. Embeds matched photos alongside repair estimates on summary sheet
            </div>
        </div>
        """, unsafe_allow_html=True)

def page_spatial():
    render_page_header("Spatial 3D Flaw Map", "spatial", "Maps each finding to a specific room on an interactive floor plan, color-coded by severity.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_realtime_badge("Spatial Mapping")

    spatial = st.session_state.spatial_data
    floor_plan = spatial.get("floor_plan", [])
    mapped = spatial.get("findings_mapped", [])

    st.markdown(f"### {len(mapped)} findings mapped to floor plan")

    with st.expander("How to Read This Floor Plan", expanded=False):
        st.markdown("**This interactive floor plan shows where each inspection finding is located in the home.**")
        st.markdown("- **Red dots** = CRITICAL issues (safety hazards, immediate attention needed)")
        st.markdown("- **Orange dots** = HIGH issues (active damage, needs repair soon)")
        st.markdown("- **Yellow dots** = MEDIUM issues (code compliance, moderate concern)")
        st.markdown("- **Green dots** = LOW issues (cosmetic, maintenance)")
        st.markdown("Hover over any dot to see what the issue is. This helps you understand the spatial distribution of problems — for example, if all issues are concentrated in one area, it may indicate a larger systemic problem.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown("### Interactive Floor Plan")
    fig = go.Figure()
    for room in floor_plan:
        x0, y0 = room.get("x", 0), room.get("y", 0)
        w, h = room.get("width", 2), room.get("height", 2)
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x0 + w, y1=y0 + h,
            line=dict(color="#475569", width=1), fillcolor="rgba(30, 41, 59, 0.6)")
        fig.add_annotation(x=x0 + w / 2, y=y0 + h / 2, text=room.get("name", ""), showarrow=False,
            font=dict(color="#94A3B8", size=10))

    for finding in mapped:
        sev_color = {"CRITICAL": "#DC2626", "HIGH": "#EA580C", "MEDIUM": "#CA8A04", "LOW": "#16A34A"}.get(finding.get("severity", "MEDIUM"), "#6B7280")
        fig.add_trace(go.Scatter(
            x=[finding.get("x_position", 0)], y=[finding.get("y_position", 0)],
            mode="markers", marker=dict(size=16, color=sev_color, symbol="circle",
                line=dict(color="white", width=2)),
            text=f"{finding.get('system', 'N/A')}: {finding.get('finding', '')[:60]}",
            hoverinfo="text", showlegend=False,
        ))

    fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(15,23,42,1)", paper_bgcolor="rgba(0,0,0,0)",
        height=500, margin=dict(t=20, b=20, l=20, r=20), xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False), yaxis_scaleanchor="x")
    st.plotly_chart(fig, width='stretch')

    st.markdown("### Findings by Location")
    for finding in mapped:
        sev_color = {"CRITICAL": "#DC2626", "HIGH": "#EA580C", "MEDIUM": "#CA8A04", "LOW": "#16A34A"}.get(finding.get("severity", "MEDIUM"), "#6B7280")
        with st.expander(f"{'🔴' if finding.get('severity') == 'CRITICAL' else '🟠' if finding.get('severity') == 'HIGH' else '🟡' if finding.get('severity') == 'MEDIUM' else '🟢'} **{finding.get('system', 'N/A')}** in {finding.get('room', 'N/A')} ({finding.get('zone', 'N/A')})", expanded=False):
            st.markdown(f"**Issue:** {finding.get('finding', '')[:150]}")
            st.markdown(f"- **Room:** {finding.get('room', 'N/A')}")
            st.markdown(f"- **Zone:** {finding.get('zone', 'N/A')}")
            st.markdown(f"- **Wall Position:** {finding.get('wall_position', 'N/A')}")

def page_audio():
    render_page_header("Voice-to-Text Inspector Audio Auditor", "audio", "Paste raw inspector notes or audio transcripts. Extracts findings, classifies severity, and maps to systems.")
    render_realtime_badge("Audio Processing")

    st.markdown("""
    <div class="callout-info" style="padding: 1.25rem; border-radius: 10px; margin-bottom: 1rem;">
        <div style="font-weight: 700; color: #93C5FD; margin-bottom: 0.5rem;">How It Works</div>
        <div style="color: #CBD5E1; font-size: 0.85rem;">
        Record raw audio notes while walking a property. The system transcribes speech to text, extracts findings, and populates the negotiation sheet before the inspector even drives home.
        </div>
    </div>
    """, unsafe_allow_html=True)

    transcript_input = st.text_area("Paste or type audio transcript here (or paste raw inspector notes):", height=200, value="")
    if st.button("Process Transcript", type="primary"):
        if transcript_input.strip():
            with st.spinner("Processing transcript..."):
                result = process_audio_transcript(transcript_input)
                st.success(f"Extracted {result['total_findings']} findings from transcript")

                col1, col2, col3 = st.columns(3)
                breakdown = result.get("severity_breakdown", {})
                with col1:
                    render_clickable_metric_with_explanation("Total Findings", str(result['total_findings']),
                        "The number of individual issues found in the transcript text. Each finding was extracted from the raw text, classified by severity, and mapped to a home system.")
                with col2:
                    render_clickable_metric_with_explanation("Critical Items", str(breakdown.get("CRITICAL", 0)),
                        "Safety hazards or structural issues found in the transcript that need immediate attention.")
                with col3:
                    render_clickable_metric_with_explanation("Systems Detected", str(len(set(f.get("system_category", "") for f in result.get("findings_extracted", [])))),
                        "The number of distinct home systems (HVAC, Plumbing, Electrical, etc.) that had findings in the transcript.")

                st.markdown("### Extracted Findings")
                for idx, finding in enumerate(result["findings_extracted"]):
                    severity = finding.get("severity", "LOW")
                    with st.expander(f"{SEVERITY_EMOJI.get(severity, '')} **{severity}** | {finding.get('system_category', 'N/A')} — {finding.get('description', '')[:100]}", expanded=(severity == "CRITICAL")):
                        st.markdown(f"**Full Description:** {finding.get('description', '')}")
                        st.markdown(f"- **System:** {finding.get('system_category', 'N/A')}")
                        st.markdown(f"- **Subsystem:** {finding.get('subsystem', 'N/A')}")
                        st.markdown(f"- **Location:** {finding.get('location', 'N/A')}")
                        st.markdown(f"- **Confidence:** {finding.get('confidence_score', 0)*100:.0f}%")
        else:
            st.warning("Please enter a transcript to process.")

def page_investor():
    render_page_header("Investor Pro Mode - ARV & Flip Margin Underwriter", "investor", "Investor-focused metrics: After Repair Value, Maximum Allowable Offer, Cap Rate, Cash-on-Cash Return, and 5-year CapEx forecast.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_property_banner()
    render_realtime_badge("Investor Analysis Q2 2026")

    investor = st.session_state.investor_analysis
    listing_price = investor.get("listing_price", 0)
    arv = investor.get("after_repair_value", 0)
    mao = investor.get("max_allowable_offer", 0)
    total_repair = investor.get("total_repair_cost", 0)
    profit = investor.get("profit_target", 0)
    cap_rate = investor.get("cap_rate", 0)
    coc = investor.get("cash_on_cash_return", 0)
    rent = investor.get("monthly_rental_estimate", 0)
    noi = investor.get("annual_noi", 0)

    deal_quality = investor.get("risk_assessment", {}).get("overall_deal_quality", {})
    grade = deal_quality.get("grade", "N/A")
    grade_color = {"A": "#10B981", "B": "#3B82F6", "C": "#F59E0B", "D": "#EF4444"}.get(grade, "#6B7280")

    profit_pct = (profit / max(listing_price, 1)) * 100 if listing_price > 0 else 0

    if grade in ["A", "B"]:
        deal_bg = "rgba(48,209,88,0.08)"
        deal_accent = "#30D158"
    elif grade == "C":
        deal_bg = "rgba(255,159,10,0.08)"
        deal_accent = "#FF9F0A"
    else:
        deal_bg = "rgba(255,69,58,0.08)"
        deal_accent = "#FF453A"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg, {deal_bg}, rgba(10,132,255,0.04));border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:1.5rem;margin-bottom:1.5rem;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">
            <div>
                <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:{deal_accent};margin-bottom:0.25rem;">Deal Analysis Dashboard</div>
                <div style="font-size:1.5rem;font-weight:800;color:#F5F5F7;">{grade} Grade — {deal_quality.get('verdict', 'N/A')}</div>
            </div>
            <div style="text-align:center;padding:0.75rem 1.5rem;background:rgba(255,255,255,0.05);border-radius:12px;border:2px solid {grade_color};">
                <div style="font-size:2.5rem;font-weight:800;color:{grade_color};">{grade}</div>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:1rem;">
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Listing Price</div>
                <div style="font-size:1.2rem;font-weight:800;color:#F5F5F7;">${listing_price:,.0f}</div>
            </div>
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">After Repair Value</div>
                <div style="font-size:1.2rem;font-weight:800;color:#30D158;">${arv:,.0f}</div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);">{((arv - listing_price) / max(listing_price, 1) * 100):+.1f}% vs listing</div>
            </div>
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Max Allowable Offer</div>
                <div style="font-size:1.2rem;font-weight:800;color:{'#30D158' if listing_price <= mao else '#FF453A'};">${mao:,.0f}</div>
                <div style="font-size:0.6rem;color:{'#30D158' if listing_price <= mao else '#FF453A'};">{'Below listing' if listing_price <= mao else 'Above listing — negotiate'}</div>
            </div>
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Total Repair Cost</div>
                <div style="font-size:1.2rem;font-weight:800;color:#FF9F0A;">${total_repair:,.0f}</div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.4);">{investor.get('deal_metrics',{}).get('repair_to_arv_ratio',0):.1f}% of ARV</div>
            </div>
            <div>
                <div style="font-size:0.6rem;color:rgba(245,245,247,0.5);text-transform:uppercase;">Target Profit</div>
                <div style="font-size:1.2rem;font-weight:800;color:{'#30D158' if profit > 0 else '#FF453A'};">${profit:,.0f}</div>
                <div style="font-size:0.6rem;color:{'#30D158' if profit > 0 else '#FF453A'};">{profit_pct:+.1f}% margin</div>
            </div>
        </div>
        <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:0.75rem;margin-top:0.75rem;">
            <div style="font-size:0.65rem;font-weight:700;color:#0A84FF;margin-bottom:0.5rem;">RECOMMENDATION</div>
            <div style="color:#CBD5E1;font-size:0.85rem;line-height:1.7;">
            {deal_quality.get('verdict', 'Analysis not available.')} {'Proceed with negotiations — this deal meets investment criteria.' if grade in ['A','B'] else 'Negotiate aggressively or consider passing — margins are thin.' if grade == 'C' else 'This deal does not meet standard investment criteria. Significant price reduction needed.'}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_clickable_metric_with_explanation("Cap Rate", f"{cap_rate:.2f}%",
            "Capitalization Rate = Annual NOI / Purchase Price. Higher is better. 8%+ is excellent. 6-8% is acceptable. Below 5% means the property isn't generating enough income relative to its cost.")
    with col2:
        render_clickable_metric_with_explanation("Cash-on-Cash", f"{coc:.2f}%",
            "Your annual return on actual cash invested (down payment + repairs). 15%+ is excellent. 10-15% is good. Below 8% means your money could work harder in index funds.")
    with col3:
        render_clickable_metric_with_explanation("Monthly Rent", f"${rent:,.0f}",
            "Estimated monthly rent based on local market data, comparable properties, and property condition after repairs.")
    with col4:
        render_clickable_metric_with_explanation("Annual NOI", f"${noi:,.0f}",
            "Net Operating Income = Annual rent minus expenses (taxes, insurance, maintenance, vacancy). This is your actual annual cash flow before debt service.")

    metrics = investor.get("deal_metrics", {})
    col1, col2, col3 = st.columns(3)
    with col1:
        render_clickable_metric_with_explanation("Repair/ARV Ratio", f"{metrics.get('repair_to_arv_ratio', 0):.1f}%",
            "Repair cost as % of ARV. Below 15% = great deal. 15-20% = normal. 20-25% = getting risky. Above 25% = repairs eating too much profit.")
    with col2:
        render_clickable_metric_with_explanation("Gross Rent Multiplier", f"{metrics.get('gross_rent_multiplier', 0):.2f}",
            "GRM = Purchase Price / Annual Rent. Lower is better. Below 12 = excellent. 12-15 = good. 15-20 = fair. Above 20 = overpaying for the rent.")
    with col3:
        render_clickable_metric_with_explanation("Breakeven Occupancy", f"{metrics.get('breakeven_occupancy_pct', 0):.1f}%",
            "% of time property must be rented to cover expenses. Below 75% = comfortable buffer. 75-85% = acceptable. Above 90% = very little margin for vacancies.")

    with st.expander("Cash Flow Analysis", expanded=True):
        annual_rent = rent * 12
        st.markdown(f"""
        <div style="padding:1rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;">
            <div style="font-size:0.7rem;font-weight:700;color:#0A84FF;margin-bottom:0.75rem;">ANNUAL CASH FLOW PROJECTION</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
                <div>
                    <div style="color:#30D158;font-size:0.65rem;font-weight:700;margin-bottom:0.25rem;">INCOME</div>
                    <div style="color:#CBD5E1;font-size:0.82rem;line-height:1.8;">
                        Gross Annual Rent: <strong style="color:#F5F5F7;">${annual_rent:,.0f}</strong><br>
                        Vacancy Allowance (5%): <strong style="color:#F5F5F7;">-${annual_rent * 0.05:,.0f}</strong><br>
                        Effective Gross Income: <strong style="color:#F5F5F7;">${annual_rent * 0.95:,.0f}</strong>
                    </div>
                </div>
                <div>
                    <div style="color:#FF453A;font-size:0.65rem;font-weight:700;margin-bottom:0.25rem;">EXPENSES</div>
                    <div style="color:#CBD5E1;font-size:0.82rem;line-height:1.8;">
                        Property Tax (est.): <strong style="color:#F5F5F7;">-${annual_rent * 0.12:,.0f}</strong><br>
                        Insurance: <strong style="color:#F5F5F7;">-${annual_rent * 0.05:,.0f}</strong><br>
                        Maintenance (5%): <strong style="color:#F5F5F7;">-${annual_rent * 0.05:,.0f}</strong><br>
                        Management (8%): <strong style="color:#F5F5F7;">-${annual_rent * 0.08:,.0f}</strong>
                    </div>
                </div>
            </div>
            <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:0.75rem;margin-top:0.75rem;text-align:center;">
                <div style="font-size:0.65rem;color:rgba(245,245,247,0.4);">NET OPERATING INCOME</div>
                <div style="font-size:1.5rem;font-weight:800;color:{'#30D158' if noi > 0 else '#FF453A'};">${noi:,.0f}/year (${noi/12:,.0f}/month)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    forecast = investor.get("depreciation_forecast", [])
    if forecast:
        with st.expander("5-Year CapEx Forecast", expanded=True):
            years = [f["year"] for f in forecast]
            costs = [f["total_expected_cost"] for f in forecast]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=years, y=costs, marker_color="#3B82F6", text=[f"${c:,.0f}" for c in costs], textposition="auto"))
            fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=300, yaxis_title="Expected CapEx Cost ($)")
            st.plotly_chart(fig, width='stretch')

            total_5yr = sum(costs)
            avg_annual = total_5yr / max(len(costs), 1)
            st.markdown(f"""
            <div style="padding:0.75rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;margin-top:0.5rem;">
                <div style="color:#CBD5E1;font-size:0.82rem;line-height:1.7;">
                    <strong style="color:#F5F5F7;">5-Year Total CapEx:</strong> ${total_5yr:,.0f} |
                    <strong style="color:#F5F5F7;">Annual Average:</strong> ${avg_annual:,.0f} |
                    <strong style="color:#F5F5F7;">Monthly Reserve Needed:</strong> ${avg_annual/12:,.0f}
                </div>
            </div>
            """, unsafe_allow_html=True)

    investment_analysis = investor.get("investment_analysis", [])
    if investment_analysis:
        with st.expander("Investment Analysis Notes", expanded=True):
            for note in investment_analysis:
                st.markdown(f"- {note}")

    risk = investor.get("risk_assessment", {})
    with st.expander("Risk Assessment", expanded=True):
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            repair_risk = risk.get("repair_risk", "N/A")
            risk_color = {"HIGH": "#FF453A", "MEDIUM": "#FF9F0A", "LOW": "#30D158"}.get(repair_risk, "#6B7280")
            st.markdown(f"**Repair Risk:** :red[{repair_risk}]" if repair_risk == "HIGH" else f"**Repair Risk:** :orange[{repair_risk}]" if repair_risk == "MEDIUM" else f"**Repair Risk:** :green[{repair_risk}]")
        with rc2:
            hold_risk = risk.get("hold_risk", "N/A")
            st.markdown(f"**Hold Risk:** :red[{hold_risk}]" if hold_risk == "HIGH" else f"**Hold Risk:** :orange[{hold_risk}]" if hold_risk == "MEDIUM" else f"**Hold Risk:** :green[{hold_risk}]")
        with rc3:
            capex_risk = risk.get("capex_risk", "N/A")
            st.markdown(f"**CapEx Risk:** :red[{capex_risk}]" if capex_risk == "HIGH" else f"**CapEx Risk:** :orange[{capex_risk}]" if capex_risk == "MEDIUM" else f"**CapEx Risk:** :green[{capex_risk}]")

    st.markdown("""
    <div class="callout-info" style="padding: 0.75rem 1rem; border-radius: 8px; margin-top: 1rem;">
        <div style="font-weight: 700; color: #93C5FD; margin-bottom: 0.3rem; font-size: 0.8rem;">Investment Disclaimer</div>
        <div style="color: #CBD5E1; font-size: 0.78rem; line-height: 1.6;">
        These projections are estimates based on publicly available data and inspection findings. Actual returns depend on market conditions, financing terms, repair scope/timing, and buyer market at resale. Always perform independent due diligence and consult with a licensed real estate professional and financial advisor before making investment decisions. Past market performance does not guarantee future results.
        </div>
    </div>
    """, unsafe_allow_html=True)

def page_escrow():
    render_page_header("Escrow Holdback & Title Binder Estimator", "escrow", "Calculates required escrow holdback amounts using standard 1.5x multiplier with milestone-based release conditions.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    render_realtime_badge("Escrow Calculator")

    escrow = st.session_state.escrow_data
    items = escrow.get("items", [])
    total = escrow.get("total_holdback", 0)

    render_clickable_metric_with_explanation("Total Escrow Holdback Required", f"${total:,.0f}",
        "Escrow holdback is money set aside at closing to pay for repairs that can't be completed before settlement. The title company holds this money and releases it to contractors as work is completed. The standard formula is Contractor Estimate x 1.5 = Holdback Amount.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    if items:
        st.markdown("### Escrow Holdback Line Items")
        for idx, item in enumerate(items):
            with st.expander(f"**{item.get('system', 'N/A')}** — Holdback: ${item.get('holdback_amount', 0):,.0f}", expanded=False):
                st.markdown(f"**Finding:** {item.get('finding', '')[:150]}")
                st.markdown(f"- **Contractor Bid:** ${item.get('contractor_bid', 0):,.0f}")
                st.markdown(f"- **Holdback (150%):** ${item.get('holdback_amount', 0):,.0f}")
                st.markdown(f"**Release Conditions:** {item.get('release_conditions', 'N/A')}")
                st.markdown(f"- **Milestone 1:** {item.get('milestone_1', 'N/A')} ({item.get('milestone_1_pct', 50)}%)")
                st.markdown(f"- **Milestone 2:** {item.get('milestone_2', 'N/A')} ({item.get('milestone_2_pct', 50)}%)")
                st.markdown("---")
                st.info("**How escrow works:** The title company holds ${:,.0f} of the seller's money. When the contractor starts work (Milestone 1), 50% is released. When work is done and passes inspection (Milestone 2), the remaining 50% is released. This protects both parties.".format(item.get('holdback_amount', 0)))

def page_brokerage_roi():
    render_page_header("Enterprise Multi-Transaction Brokerage ROI Dashboard", "roi", "Aggregated performance metrics for managing brokers. Tracks total credits negotiated and agent success rates.")
    render_realtime_badge("Brokerage Performance")

    roi_data = generate_brokerage_roi_data()
    summary = roi_data.get("summary", {})

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(render_metric_card("Total Agents", str(summary.get("total_agents", 0))), unsafe_allow_html=True)
    with col2:
        st.markdown(render_metric_card("Transactions", str(summary.get("total_transactions", 0))), unsafe_allow_html=True)
    with col3:
        st.markdown(render_metric_card("Credits Negotiated", f"${summary.get('total_credits_negotiated', 0):,.0f}"), unsafe_allow_html=True)
    with col4:
        st.markdown(render_metric_card("Revenue Impact", f"${summary.get('estimated_team_revenue_impact', 0):,.0f}"), unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown("### Agent Performance Rankings")
    agents = roi_data.get("agent_performance", [])
    if agents:
        agent_df = pd.DataFrame(agents)
        agent_df = agent_df.rename(columns={
            "name": "Agent", "total_transactions": "Deals",
            "total_credits_negotiated": "Total Credits", "avg_credit_per_deal": "Avg Credit/Deal",
            "success_rate": "Success Rate %"
        })
        st.dataframe(agent_df[["Agent", "Deals", "Total Credits", "Avg Credit/Deal", "Success Rate %"]], width='stretch', hide_index=True)

    if agents:
        st.markdown("### Credits Negotiated by Agent")
        fig = px.bar(
            x=[a["name"] for a in agents], y=[a["total_credits_negotiated"] for a in agents],
            color=[a["success_rate"] for a in agents],
            color_continuous_scale="Viridis",
            labels={"x": "Agent", "y": "Total Credits ($)", "color": "Success Rate %"},
        )
        fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=350)
        st.plotly_chart(fig, width='stretch')

    st.markdown("### Team Insights")
    for insight in roi_data.get("insights", []):
        st.markdown(f"""
        <div class="callout-info" style="padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 0.5rem;">
            <div style="color: #CBD5E1; font-size: 0.85rem;">{insight}</div>
        </div>
        """, unsafe_allow_html=True)

def page_seo():
    render_page_header("Programmatic Local SEO Land-Grab Engine", "seo", "Auto-generates SEO-optimized landing pages for each system type in the property's ZIP code.")
    render_realtime_badge("SEO Intelligence")
    zip_code = st.text_input("Target ZIP Code for SEO Pages", value=st.session_state.get("property_data", {}).get("zip_code", "90210"))
    if st.button("Generate SEO Landing Pages", type="primary"):
        with st.spinner("Generating programmatic pages..."):
            seo = generate_seo_landing_pages(zip_code, {"modifier": 1.0})
            analytics = generate_seo_analytics(seo.get("pages", []))
            st.session_state.seo_result = seo
            st.session_state.seo_analytics = analytics

    if st.session_state.get("seo_result"):
        seo = st.session_state.seo_result
        analytics = st.session_state.seo_analytics

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(render_metric_card("Pages Generated", str(seo.get("total_pages", 0))), unsafe_allow_html=True)
        with col2:
            st.markdown(render_metric_card("Est. Monthly Traffic", f"{seo.get('total_estimated_traffic', 0):,}"), unsafe_allow_html=True)
        with col3:
            st.markdown(render_metric_card("Total Impressions", f"{analytics.get('total_impressions', 0):,}"), unsafe_allow_html=True)
        with col4:
            st.markdown(render_metric_card("Monthly Lead Value", f"${analytics.get('estimated_monthly_value', 0):,}"), unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        for idx, page in enumerate(seo.get("pages", [])):
            with st.expander(f"📄 {page.get('page_title', 'N/A')}", expanded=False):
                st.markdown(f"**URL Slug:** /{page.get('page_slug', 'N/A')}")
                st.markdown(f"**Meta Description:** {page.get('meta_description', '')}")
                st.markdown(f"- **Average Repair Cost:** ${page.get('avg_cost', 0):,.0f}")
                st.markdown(f"- **Estimated Monthly Traffic:** {page.get('estimated_monthly_traffic', 0):,} visits/month")
                st.markdown(f"- **Keyword Difficulty:** {page.get('keyword_difficulty', 0):.0f}/100")
                st.markdown(f"- **Target Keyword:** {page.get('target_keyword', 'N/A')}")
                st.markdown("---")
                city_name = st.session_state.get("property_data", {}).get("city", "your area")
                st.info(f"**What this page does:** This SEO landing page targets homeowners in {city_name} searching for '{page.get('target_keyword', 'repair costs')}' on Google. It captures organic traffic from people researching repair costs, generating leads for your brokerage.")

def page_lead_magnet():
    render_page_header("White-Label Inspection Lead Magnet Widget", "lead_magnet", "Client-facing widget for your website. Buyers upload their inspection PDF, get a preview, then enter contact info to unlock the full report.")
    agent_name = st.text_input("Agent Name", "Sarah Chen")
    agent_email = st.text_input("Agent Email", "sarah@brokerage.com")
    config = generate_lead_magnet_widget_config(agent_name, agent_email)

    st.markdown(f"""
    <div style="background: var(--bg-card); border: 2px solid var(--primary-light); border-radius: var(--radius-lg); padding: 2rem; max-width: 500px; margin-bottom: 1rem;">
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <div style="font-size: 1.5rem; font-weight: 800; color: #F1F5F9;">{config['widget_title']}</div>
            <div style="color: #94A3B8; font-size: 0.9rem;">{config['widget_subtitle']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("lead_magnet_form"):
        st.markdown("**Upload your inspection PDF**")
        lead_file = st.file_uploader("Drop PDF here", type=["pdf"], label_visibility="collapsed")
        lead_email = st.text_input("Your email address")
        lead_phone = st.text_input("Your phone number")
        submitted = st.form_submit_button(config.get('cta_button', 'Get My Free Report'))
        if submitted:
            if lead_email:
                st.success(f"Thank you! A full analysis report will be sent to {lead_email}. (Lead captured: {lead_email} | {lead_phone})")
            else:
                st.warning("Please enter your email address to receive the full report.")

    st.markdown(f"""
    <div style="color: #64748B; font-size: 0.75rem; text-align: center; margin-top: 0.75rem;">{config.get('social_proof', '')}</div>
    """, unsafe_allow_html=True)

def page_export():
    render_page_header("Export Professional Report Package", "export", "Download the complete analysis in multiple formats: Full HTML report, CSV spreadsheet, text report.")
    if not st.session_state.get("analysis_complete"):
        st.warning("Please upload and process a report first.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Comprehensive Exports (All 21 Modules)")

        try:
            pdf_html = generate_pdf_report(
                st.session_state.property_data, st.session_state.findings,
                st.session_state.cost_matrix, st.session_state.market_profile,
                st.session_state.get("insurance_analysis", {}),
                st.session_state.get("environmental_data"),
                st.session_state.get("permit_data"),
                st.session_state.get("recall_data"),
                st.session_state.get("negotiation_strategies"),
                st.session_state.get("capex_analysis"),
                st.session_state.get("depreciation_data"),
                st.session_state.get("escrow_data"),
                st.session_state.get("contractor_bids"),
                st.session_state.get("spatial_data"),
                st.session_state.get("investor_analysis"),
            )
            st.download_button("📄 Download Full Report (HTML/PDF)", pdf_html, file_name="repair_cost_analysis_report.html", mime="text/html", width='stretch')
        except Exception as e:
            st.error(f"PDF export error: {e}")

        try:
            csv_data = generate_csv_export(
                st.session_state.findings, st.session_state.cost_matrix,
                st.session_state.get("market_profile"),
                st.session_state.get("insurance_analysis", {}),
                st.session_state.get("environmental_data"),
                st.session_state.get("permit_data"),
                st.session_state.get("recall_data"),
                st.session_state.get("negotiation_strategies"),
                st.session_state.get("capex_analysis"),
                st.session_state.get("depreciation_data"),
                st.session_state.get("escrow_data"),
                st.session_state.get("contractor_bids"),
                st.session_state.get("spatial_data"),
                st.session_state.get("investor_analysis"),
                st.session_state.get("property_data"),
            )
            st.download_button("📊 Download Full CSV Spreadsheet", csv_data, file_name="repair_cost_analysis_data.csv", mime="text/csv", width='stretch')
        except Exception as e:
            st.error(f"CSV export error: {e}")

        try:
            txt_data = generate_text_report(
                st.session_state.property_data, st.session_state.findings,
                st.session_state.cost_matrix, st.session_state.market_profile,
                st.session_state.get("insurance_analysis", {}),
                st.session_state.get("environmental_data"),
                st.session_state.get("permit_data"),
                st.session_state.get("recall_data"),
                st.session_state.get("negotiation_strategies"),
                st.session_state.get("capex_analysis"),
                st.session_state.get("depreciation_data"),
                st.session_state.get("escrow_data"),
                st.session_state.get("contractor_bids"),
                st.session_state.get("spatial_data"),
                st.session_state.get("investor_analysis"),
            )
            st.download_button("📝 Download Text Report", txt_data, file_name="repair_cost_analysis_report.txt", mime="text/plain", width='stretch')
        except Exception as e:
            st.error(f"Text export error: {e}")

        try:
            report = generate_comprehensive_report(
                st.session_state.property_data, st.session_state.findings,
                st.session_state.cost_matrix, st.session_state.depreciation_data,
                st.session_state.market_profile, st.session_state.capex_analysis,
                st.session_state.negotiation_strategies, st.session_state.insurance_analysis,
                st.session_state.environmental_data, st.session_state.escrow_data,
                st.session_state.permit_data, st.session_state.recall_data,
            )
            st.download_button("📋 Download JSON Data", json.dumps(report, indent=2, default=str), file_name="repair_cost_analysis_data.json", mime="application/json", width='stretch')
        except Exception as e:
            st.error(f"JSON export error: {e}")

    with col2:
        st.markdown("### Report Summary")
        findings = st.session_state.findings
        cost_matrix = st.session_state.cost_matrix
        summary = cost_matrix.get("summary", {})

        st.metric("Total Findings", len(findings))
        st.metric("Estimated Cost Range", f"${summary.get('total_low', 0):,.0f} - ${summary.get('total_high', 0):,.0f}")
        st.metric("Average Estimate", f"${summary.get('total_avg', 0):,.0f}")

        severity_breakdown = summary.get("by_severity", {})
        for sev, count in severity_breakdown.items():
            if count > 0:
                st.markdown(f"**{sev}:** {count} findings")

        st.markdown("---")
        st.markdown("""
        <div style="padding: 1rem; border-radius: 8px; background: rgba(10, 132, 255, 0.1); border: 1px solid rgba(10, 132, 255, 0.3);">
            <div style="font-weight: 700; color: #0A84FF; margin-bottom: 0.5rem;">Export Features</div>
            <div style="color: #CBD5E1; font-size: 0.85rem;">
            ✅ Full HTML report with interactive sections<br>
            ✅ Comprehensive CSV with all 21 modules<br>
            ✅ Professional text report<br>
            ✅ Structured JSON data export<br>
            ✅ Dark-theme print-ready PDF format
            </div>
        </div>
        """, unsafe_allow_html=True)

def _generate_sample_findings():
    return [
        {"id": 1, "system_category": "HVAC", "subsystem": "heat exchanger", "component": "HVAC", "location": "Basement utility area", "description": "Rust on heat exchanger coils, inducer motor noisy. Model: Carrier (Mfg: 2012). System is 14 years old, past typical 12-year lifespan. Carbon monoxide safety risk identified.", "severity": "CRITICAL", "severity_score": 1, "confidence_score": 0.92, "photos_matched": []},
        {"id": 2, "system_category": "ROOF", "subsystem": "step flashing", "component": "Roofing", "location": "Chimney structure area", "description": "Damaged step flashing around chimney structure; localized attic moisture reading 18%. Active water intrusion pathway identified. Risk of rot spread if unaddressed through winter.", "severity": "HIGH", "severity_score": 2, "confidence_score": 0.88, "photos_matched": []},
        {"id": 3, "system_category": "ELECTRICAL", "subsystem": "GFCI outlet", "component": "Electrical", "location": "Kitchen prep area", "description": "Three ungrounded GFCI outlets identified in primary kitchen prep area. Code violation for current NEC standards. No ground wire present in circuit.", "severity": "MEDIUM", "severity_score": 3, "confidence_score": 0.90, "photos_matched": []},
        {"id": 4, "system_category": "PLUMBING", "subsystem": "drain", "component": "Plumbing", "location": "Secondary bathroom", "description": "Slow drain response in secondary bathroom sink basin. P-trap appears to have minor buildup. Standard operational wear consistent with property age.", "severity": "LOW", "severity_score": 4, "confidence_score": 0.82, "photos_matched": []},
        {"id": 5, "system_category": "PLUMBING", "subsystem": "water heater", "component": "Plumbing", "location": "Garage utility area", "description": "Water heater showing active corrosion at base. Rheem 2014 model, approximately 12 years old. Bottom valve has visible rust and mineral deposits. T&P valve shows signs of past discharge.", "severity": "HIGH", "severity_score": 2, "confidence_score": 0.87, "photos_matched": []},
        {"id": 6, "system_category": "EXTERIOR", "subsystem": "deck", "component": "Exterior", "location": "Rear of property", "description": "Deck missing handrail on primary access stairs. Baluster spacing exceeds 4-inch code requirement. Wood rot detected at ledger board connection.", "severity": "HIGH", "severity_score": 2, "confidence_score": 0.85, "photos_matched": []},
        {"id": 7, "system_category": "FOUNDATION", "subsystem": "crack", "component": "Structural", "location": "North wall basement", "description": "Horizontal crack observed in foundation wall on north side, approximately 18 inches long. May indicate lateral soil pressure or settling. Engineering assessment recommended.", "severity": "HIGH", "severity_score": 2, "confidence_score": 0.80, "photos_matched": []},
        {"id": 8, "system_category": "MOISTURE", "subsystem": "mold", "component": "Environmental", "location": "Crawl space", "description": "Active mold growth observed on floor joists in crawl space. Approximately 40 square feet affected. Moisture source appears to be missing vapor barrier. Remediation required.", "severity": "CRITICAL", "severity_score": 1, "confidence_score": 0.85, "photos_matched": []},
        {"id": 9, "system_category": "EXTERIOR", "subsystem": "window", "component": "Windows & Doors", "location": "Master bedroom", "description": "Failed seal on double-pane window. Condensation between panes indicates seal failure. Minor draft detected. Window is approximately 18 years old.", "severity": "LOW", "severity_score": 4, "confidence_score": 0.88, "photos_matched": []},
        {"id": 10, "system_category": "ELECTRICAL", "subsystem": "panel", "component": "Electrical", "location": "Garage", "description": "Federal Pacific Stab-Lok electrical panel identified. Known fire hazard with breaker failure history. Multiple recalls and class action lawsuits. Panel replacement strongly recommended.", "severity": "CRITICAL", "severity_score": 1, "confidence_score": 0.95, "photos_matched": []},
        {"id": 11, "system_category": "HVAC", "subsystem": "duct", "component": "HVAC", "location": "Attic", "description": "Flexible duct connections in attic show signs of disconnection and compression. Energy loss estimated at 20-30%. Insulation at duct joints is deteriorated.", "severity": "MEDIUM", "severity_score": 3, "confidence_score": 0.83, "photos_matched": []},
        {"id": 12, "system_category": "ROOF", "subsystem": "shingles", "component": "Roofing", "location": "South-facing slope", "description": "Significant granule loss on south-facing roof slope. Curling and lifting observed on approximately 15% of shingles. Roof is approximately 20 years old with 25-year rated shingles.", "severity": "MEDIUM", "severity_score": 3, "confidence_score": 0.85, "photos_matched": []},
    ]

def _generate_sample_report_text():
    return """HOME INSPECTION REPORT

Property: 1428 Elm Street, Beverly Hills, CA 90210
Inspection Date: 2026-07-10
Inspector: John Smith, Licensed Home Inspector

SUMMARY OF FINDINGS

HVAC System:
Rust on heat exchanger coils, inducer motor noisy. Model: Carrier (Mfg: 2012). System is 14 years old, past typical 12-year lifespan. Carbon monoxide safety risk identified. Immediate professional evaluation recommended.

Roofing:
Damaged step flashing around chimney structure; localized attic moisture reading 18%. Active water intrusion pathway identified. Risk of rot spread if unaddressed through winter. Licensed roofer repair required.

Electrical:
Three ungrounded GFCI outlets identified in primary kitchen prep area. Code violation for current NEC standards. Federal Pacific Stab-Lok electrical panel identified in garage. Known fire hazard.

Plumbing:
Slow drain response in secondary bathroom sink basin. Water heater showing active corrosion at base. Rheem 2014 model, approximately 12 years old.

Exterior:
Deck missing handrail on primary access stairs. Baluster spacing exceeds 4-inch code requirement. Wood rot detected at ledger board connection.

Structural:
Horizontal crack observed in foundation wall on north side, approximately 18 inches long.

Environmental:
Active mold growth observed on floor joists in crawl space. Approximately 40 square feet affected."""

if not st.session_state.get("analysis_complete"):
    page_upload()
else:
    MODULES = [
        ("Cost Analysis", page_cost_analysis),
        ("Depreciation & CapEx", page_depreciation),
        ("Market & Negotiation", page_market),
        ("Contractor Bids", page_contractor_bids),
        ("Credit Sandbox", page_sandbox),
        ("Legal Addendum", page_legal),
        ("Insurance Risk", page_insurance),
        ("Environmental Risk", page_environmental),
        ("Permits & Records", page_permits),
        ("Recall Check", page_recalls),
        ("Photo Evidence", page_photos),
        ("Spatial Map", page_spatial),
        ("Investor Analysis", page_investor),
        ("Escrow Calculator", page_escrow),
        ("Export Report", page_export),
        ("Audio / Voice", page_audio),
        ("Brokerage ROI", page_brokerage_roi),
        ("SEO Pages", page_seo),
        ("Lead Magnet", page_lead_magnet),
    ]

    MODULE_NAMES = [name for name, _ in MODULES]

    with st.sidebar:
        st.markdown("### 📋 Analysis Modules")
        st.markdown("---")
        selected = st.radio(
            "Module",
            MODULE_NAMES,
            key="_nav_radio",
            label_visibility="collapsed",
        )

    for name, func in MODULES:
        if name == selected:
            try:
                func()
            except Exception as e:
                import traceback
                st.error(f"**Module Error ({name}):** {str(e)}")
                with st.expander("Details"):
                    st.code(traceback.format_exc())
            break

    st.markdown(f"""<div style="background:#1a0000;border:2px solid #FF453A;border-radius:8px;padding:12px 16px;margin-top:24px;font-family:monospace;font-size:12px;color:#FF6961;">
    <b>DEBUG:</b> Selected = "{selected}" | Modules loaded = {len(MODULES)} | Streamlit {st.__version__}
    </div>""", unsafe_allow_html=True)

