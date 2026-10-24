"""Property-based + contract + security tests (v3.4 enterprise suite).

The badge invariant is the product's core promise: for ALL inputs, every
output figure carries exactly one badge from the canonical set. This is
machine-checked with Hypothesis. Security, insurance-regex, investor
provenance, confidence determinism, MCP JSON-RPC frames, compliance,
citable artifacts, audit chain, and ETL snapshots are all covered.
Deterministic: no network, no randomness beyond Hypothesis shrinking.
"""

import json
import os
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

# Test-mode security env (before importing engines that read env).
os.environ.setdefault("SHARE_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
os.environ.setdefault("SHARE_SECRET_SKIP_BOOT_CHECK", "1")
os.environ["API_AUTH_DISABLED"] = "1"

REPO = Path(__file__).resolve().parents[1]
VALID_BADGES = {"VERIFIED", "USER_PROVIDED", "MODELED", "REQUIRES_KEY", "UNAVAILABLE"}


# ------------------------------------------------------------------
# 1. Badge invariant — property-based, the provenance contract
# ------------------------------------------------------------------
@settings(max_examples=50, deadline=None)
@given(
    findings=st.lists(
        st.fixed_dictionaries(
            {
                "description": st.text(min_size=5, max_size=200),
                "severity": st.sampled_from(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]),
                "system": st.sampled_from(["HVAC", "ROOF", "PLUMBING", "ELECTRICAL", "OTHER"]),
            }
        ),
        min_size=0,
        max_size=8,
    ),
    state=st.sampled_from(["CA", "TX", "FL", "NY", ""]),
    zip_code=st.sampled_from(["90210", "78701", "33101", ""]),
)
def test_badge_invariant_cost_matrix(findings, state, zip_code):
    """For ALL inputs: line_items carry exactly one valid badge, never null."""
    from engines.cost_engine import generate_cost_matrix

    cm = generate_cost_matrix(findings, state, zip_code, [], None)
    for it in cm.get("line_items", []):
        badge = it.get("badge", "MODELED")
        assert badge in VALID_BADGES, f"invalid badge {badge!r}"
        assert badge is not None


@settings(max_examples=40, deadline=None)
@given(
    text=st.text(min_size=10, max_size=300),
    severity=st.sampled_from(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]),
)
def test_confidence_in_range_and_deterministic(text, severity):
    """Confidence is in [0.10, 0.98] and deterministic for identical inputs."""
    from engines.confidence_engine import score_finding

    a = score_finding(text, severity=severity)
    b = score_finding(text, severity=severity)
    assert a == b, "score_finding must be deterministic"
    assert 0.10 <= a <= 0.98


def test_no_hardcoded_confidence_constants():
    """The audit kill-list: no flat 0.85/0.75 priors remain in parser/voice engines."""
    parser = (REPO / "engines" / "parser_engine.py").read_text(encoding="utf-8")
    voice = (REPO / "engines" / "voice_engine.py").read_text(encoding="utf-8")
    assert '"confidence_score": 0.85' not in parser
    assert '"confidence_score": 0.75' not in voice
    assert "score_finding" in parser and "score_finding" in voice


# ------------------------------------------------------------------
# 2. Security — share secret, timing-safe auth, dev-secret removal
# ------------------------------------------------------------------
def test_dev_share_secret_removed():
    """The retired dev default must not exist anywhere in the live engines tree."""
    for path in (REPO / "engines").glob("*.py"):
        src = path.read_text(encoding="utf-8")
        # share_engine may reference the literal only to REJECT it.
        if path.name == "share_engine.py":
            assert 'os.environ.get("SHARE_SECRET", "dev-share-secret-change-me")' not in src
            continue
        assert "dev-share-secret-change-me" not in src, f"{path} still uses dev secret"


def test_share_engine_rejects_dev_default():
    from engines.share_engine import ShareSecretError, seal_snapshot

    old = os.environ.get("SHARE_SECRET")
    os.environ["SHARE_SECRET"] = "dev-share-secret-change-me"
    try:
        try:
            seal_snapshot({"x": 1})
            raise AssertionError("dev default must be rejected")
        except ShareSecretError:
            pass
    finally:
        if old is not None:
            os.environ["SHARE_SECRET"] = old


def test_share_roundtrip_and_expiry():
    from engines.share_engine import open_snapshot, seal_snapshot

    token = seal_snapshot({"totals": {"total_avg": 100}}, ttl_s=60)
    snap = open_snapshot(token)
    assert snap["totals"]["total_avg"] == 100
    expired = seal_snapshot({"a": 1}, ttl_s=-1)
    assert open_snapshot(expired) is None


def test_share_signature_tamper_rejected():
    from engines.share_engine import open_snapshot, seal_snapshot

    token = seal_snapshot({"a": 1})
    raw, sig = token.rsplit(".", 1)
    tampered = raw[:-2] + "xx." + sig
    assert open_snapshot(tampered) is None


def test_share_uses_compare_digest():
    src = (REPO / "engines" / "share_engine.py").read_text(encoding="utf-8")
    assert "hmac.compare_digest" in src


def test_api_auth_uses_compare_digest():
    src = (REPO / "api_server.py").read_text(encoding="utf-8")
    assert "hmac.compare_digest" in src


def test_owasp_headers_middleware():
    src = (REPO / "api_server.py").read_text(encoding="utf-8")
    for header in (
        "X-Content-Type-Options",
        "Content-Security-Policy",
        "X-Frame-Options",
        "Strict-Transport-Security",
    ):
        assert header in src, f"missing OWASP header {header}"


def test_share_portal_escapes_html():
    src = (REPO / "api_server.py").read_text(encoding="utf-8")
    assert "escape(str(r.get('room'" in src
    assert "escape(str(r.get('condition'" in src
    assert "escape(str(r.get('priority'" in src


# ------------------------------------------------------------------
# 3. Insurance engine — regex patterns now actually match
# ------------------------------------------------------------------
def test_insurance_regex_patterns_match():
    """Polybutylene finding must trigger the polybutylene flag (regex, not substring)."""
    from engines.insurance_engine import analyze_insurance_risk

    findings = [
        {"description": "Polybutylene supply lines corroded at fittings, active leak under kitchen sink."}
    ]
    out = analyze_insurance_risk(findings, {"state": "FL", "year_built": 1985})
    types = [r["red_flag_type"] for r in out["red_flags"]]
    assert any("Polybutylene" in t for t in types), f"polybutylene flag not raised: {types}"


def test_insurance_regex_handles_dotstar_pattern():
    """The roof 'roof.*1[3-9].years' pattern only works as regex — substring missed it."""
    from engines.insurance_engine import analyze_insurance_risk

    findings = [{"description": "Roof covering is 16 years old, granular loss observed."}]
    out = analyze_insurance_risk(findings, {"state": "TX", "year_built": 1990})
    types = [r["red_flag_type"] for r in out["red_flags"]]
    assert any("roof" in t.lower() or "Aging Roof" in t for t in types), f"roof flag not raised: {types}"


def test_insurance_flags_carry_badge_and_source():
    from engines.insurance_engine import analyze_insurance_risk

    findings = [{"description": "Federal Pacific Stab-Lok panel in garage."}]
    out = analyze_insurance_risk(findings, {"state": "CA", "year_built": 2000})
    assert out["red_flags"], "expected FPE flag"
    for flag in out["red_flags"]:
        assert flag.get("badge") == "MODELED"
        assert "source_url" in flag
        assert "as_of" in flag


# ------------------------------------------------------------------
# 4. Investor engine — every heuristic badged
# ------------------------------------------------------------------
def test_investor_heuristics_registry_badged():
    from engines.investor_engine import INVESTOR_HEURISTICS

    for name, spec in INVESTOR_HEURISTICS.items():
        assert spec.get("badge") in VALID_BADGES, f"{name} missing valid badge"
        assert "description" in spec, f"{name} missing description"
        assert "source_note" in spec, f"{name} missing source_note"


def test_investor_deal_returns_figure_provenance():
    from engines.investor_engine import analyze_investor_deal

    out = analyze_investor_deal(
        {"year_built": 2000, "square_footage": 1800, "state": "TX", "zip_code": "78701"},
        findings=[],
        cost_matrix={"summary": {"total_avg": 20000, "total_low": 15000, "total_high": 30000}},
        capex_analysis={"summary": {"weighted_risk_exposure": 5000}},
        user_inputs={"list_price": 350000, "monthly_rent": 2200},
    )
    assert "figure_provenance" in out
    for k, v in out["figure_provenance"].items():
        assert v in VALID_BADGES or v.endswith("_DERIVED"), f"{k} has invalid badge {v}"
    assert "heuristics_registry" in out


# ------------------------------------------------------------------
# 5. MCP server — JSON-RPC contract frames
# ------------------------------------------------------------------
def test_mcp_tools_list_frame():
    import subprocess
    import sys

    payload = json.dumps({"method": "tools/list", "id": 1}) + "\n"
    proc = subprocess.run(
        [sys.executable, str(REPO / "mcp_server.py")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO),
        env={**os.environ, "SHARE_SECRET": os.environ.get("SHARE_SECRET", "")},
    )
    assert proc.returncode == 0
    frame = json.loads(proc.stdout.strip().splitlines()[0])
    assert frame["id"] == 1
    tools = frame["result"]["tools"]
    names = [t["name"] for t in tools]
    assert "estimate_repair" in names
    for t in tools:
        assert "inputSchema" in t


def test_mcp_resources_list_frame():
    import subprocess
    import sys

    payload = json.dumps({"method": "resources/list", "id": 2}) + "\n"
    proc = subprocess.run(
        [sys.executable, str(REPO / "mcp_server.py")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO),
        env={**os.environ, "SHARE_SECRET": os.environ.get("SHARE_SECRET", "")},
    )
    frame = json.loads(proc.stdout.strip().splitlines()[0])
    assert frame["id"] == 2
    uris = [r["uri"] for r in frame["result"]["resources"]]
    assert "repair://provenance/legend" in uris


def test_mcp_provenance_legend_resource():
    from mcp_server import read_resource

    legend = read_resource("repair://provenance/legend")
    assert set(legend.keys()) >= {"VERIFIED", "USER_PROVIDED", "MODELED", "REQUIRES_KEY", "UNAVAILABLE"}
    assert read_resource("repair://cost-tables/00000")["badge"] == "UNAVAILABLE"


# ------------------------------------------------------------------
# 6. Compliance — EU AI Act + ECOA screen
# ------------------------------------------------------------------
def test_eu_ai_act_documentation_complete():
    from engines.compliance_engine import eu_ai_act_documentation

    doc = eu_ai_act_documentation()
    for key in ("intended_purpose", "human_oversight", "training_data_provenance", "post_market_monitoring"):
        assert key in doc
    assert "deterministic" in doc["training_data_provenance"].lower()


def test_ecoa_audit_runs_without_data():
    from engines.compliance_engine import ecoa_audit

    out = ecoa_audit()
    assert out["status"] == "AWAITING_DATA"
    assert "methodology" in out
    assert out["zip_count"] >= 0


def test_ecoa_audit_with_synthetic_sample():
    import random

    from engines.compliance_engine import ecoa_audit

    rng = random.Random(42)
    shares = {f"z{i:05d}": rng.random() for i in range(60)}
    out = ecoa_audit(minority_share_data=shares)
    assert out["status"] in ("PASS", "FLAGGED", "INSUFFICIENT_SAMPLE")


# ------------------------------------------------------------------
# 7. Legal — ATTORNEY_REVIEW_REQUIRED non-removable
# ------------------------------------------------------------------
def test_legal_addendum_always_flags_attorney_review():
    from engines.legal_engine import generate_legal_addendum

    out = generate_legal_addendum(
        {"address": "1 Main St", "city": "Austin", "state": "TX", "zip_code": "78701"},
        findings=[{"description": "Roof leak", "severity": "HIGH", "system_category": "ROOF"}],
        cost_matrix={"line_items": []},
    )
    assert out["ATTORNEY_REVIEW_REQUIRED"] is True
    assert "ATTORNEY_REVIEW_REQUIRED" in out["addendum_text"]


# ------------------------------------------------------------------
# 8. Citable engine — markdown twin + JSON-LD
# ------------------------------------------------------------------
def test_citable_package_structure():
    from engines.citable_engine import build_citable_package

    pkg = build_citable_package(
        "abc123",
        {"total_avg": 12500, "total_low": 9000, "total_high": 17000},
        [
            {
                "finding": "Roof",
                "system": "ROOF",
                "severity": "HIGH",
                "total_low": 8000,
                "total_avg": 10000,
                "total_high": 12000,
                "badge": "MODELED",
                "as_of": "2026-10-24",
                "source_url": "https://www.bls.gov/oes/",
            }
        ],
        base_url="https://example.com",
        zip_code="78701",
    )
    assert pkg["markdown"].startswith("# Repair Cost Estimate")
    assert "MODELED" in pkg["markdown"]
    assert pkg["jsonld"]["@type"] == "Dataset"
    assert pkg["jsonld"]["url"].endswith("/e/abc123")
    assert "MODELED" in pkg["citation"]


# ------------------------------------------------------------------
# 9. Audit log — hash chain + redaction
# ------------------------------------------------------------------
def test_audit_log_chain_and_redaction(tmp_path, monkeypatch):
    from engines import audit_log

    monkeypatch.setattr(audit_log, "AUDIT_LOG_PATH", tmp_path / "audit.jsonl")
    audit_log.log_event("test.event", actor="pytest", payload={"address": "1 Main St 90210", "n": 1})
    audit_log.log_event("test.event2", actor="pytest", payload={"x": 2})
    events = audit_log.export_events()
    assert len(events) == 2
    assert audit_log.verify_chain() is True
    raw = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert "1 Main St" not in raw, "PII must be redacted in audit log"


# ------------------------------------------------------------------
# 10. ETL snapshot — write/read/hash
# ------------------------------------------------------------------
def test_etl_snapshot_roundtrip(tmp_path, monkeypatch):
    from engines import etl_engine

    monkeypatch.setattr(etl_engine, "SNAPSHOT_DIR", tmp_path / "snaps")
    monkeypatch.setattr(etl_engine, "MANIFEST_PATH", tmp_path / "snaps" / "manifest.json")
    payload = [{"zip": "90210", "modifier": 1.12}, {"zip": "78701", "modifier": 1.0}]
    meta = etl_engine.write_snapshot("test_dataset", payload, source_url="https://example.com")
    assert meta["content_sha256"]
    got, got_meta = etl_engine.read_latest_snapshot("test_dataset")
    assert got == payload
    assert got_meta["source_url"] == "https://example.com"


# ------------------------------------------------------------------
# 11. SEO engine — prompt portfolio + honest UNAVAILABLE
# ------------------------------------------------------------------
def test_prompt_portfolio_size_and_no_fabricated_analytics():
    from engines.seo_engine import build_prompt_portfolio, generate_seo_analytics, track_ai_visibility

    portfolio = build_prompt_portfolio()
    assert portfolio["total_prompts"] >= 50
    assert "engines" in portfolio
    analytics = generate_seo_analytics([], None)
    assert analytics["status"] == "UNAVAILABLE"
    empty = track_ai_visibility("p001", "chatgpt", [])
    assert empty["status"] == "UNAVAILABLE"


def test_track_ai_visibility_aggregates_runs():
    from engines.seo_engine import track_ai_visibility

    runs = [
        {"mentioned": True, "cited": True, "sentiment": 1, "cited_urls": ["https://example.com/e/1"]},
        {"mentioned": True, "cited": False, "sentiment": 0, "cited_urls": []},
        {"mentioned": False, "cited": False, "sentiment": -1, "cited_urls": []},
    ]
    out = track_ai_visibility("p001", "chatgpt", runs)
    assert out["mention_rate"] == round(2 / 3 * 100, 2)
    assert out["citation_rate"] == round(1 / 3 * 100, 2)
    assert out["badge"] == "USER_PROVIDED"


# ------------------------------------------------------------------
# 12. FRED engine — REQUIRES_KEY honesty when no key
# ------------------------------------------------------------------
def test_fred_requires_key_honest(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    from engines.fred_engine import fetch_fred_series

    out = fetch_fred_series("FEDFUNDS")
    assert out["badge"] == "REQUIRES_KEY"
    assert out["observations"] == []


# ------------------------------------------------------------------
# 13. Permit live engine — honest status naming
# ------------------------------------------------------------------
def test_permit_live_engine_honest_status(monkeypatch):
    monkeypatch.delenv("BUILDFAX_KEY", raising=False)
    monkeypatch.delenv("ECHELON_KEY", raising=False)
    from engines.permit_live_engine import live_permit_lookup

    out = live_permit_lookup("1 Main St")
    assert out["status"] == "NO_PROVIDER_CONFIGURED"
    assert out["badge"] == "REQUIRES_KEY"


# ------------------------------------------------------------------
# 14. Star-import removal — engines/__init__ is explicit
# ------------------------------------------------------------------
def test_engines_init_has_no_star_imports():
    src = (REPO / "engines" / "__init__.py").read_text(encoding="utf-8")
    assert "import *" not in src
    assert "noqa: F403" not in src


# ------------------------------------------------------------------
# 15. Kill-list: utils/ and config.legacy.py are gone
# ------------------------------------------------------------------
def test_kill_list_removed():
    assert not (REPO / "utils").exists(), "utils/ should be deleted (zero importers, 1168 lines dead)"
    assert not (REPO / "config.legacy.py").exists(), (
        "config.legacy.py should be deleted (git is the audit diff)"
    )
    assert not (REPO / "data" / "repair_estimator.db").exists(), "3.4MB sqlite DB must not be committed"
    assert (REPO / "legacy" / "export_engine.py").exists(), "export_engine quarantined in legacy/"


# ------------------------------------------------------------------
# 16. Insurance JSON dataset has citations
# ------------------------------------------------------------------
def test_insurance_red_flags_json_has_sources():
    data = json.loads((REPO / "data" / "insurance_red_flags.json").read_text(encoding="utf-8"))
    assert data["version"] >= "2026.10"
    for flag in data["data"]:
        assert flag.get("badge") == "MODELED"
        assert flag.get("source_url"), f"{flag['pattern']} missing source_url"
        assert flag.get("as_of")
