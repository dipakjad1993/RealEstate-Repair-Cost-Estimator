"""October regressions: escrow crash, parser quality, enterprise UI/brand.

Covers the AttributeError ('str' has no 'get') that fired when bids arrived
dict-shaped, the parser junk findings (42 → 10 on the sample report), and
the Google Sans Flex / gradient enterprise skin across every surface.
"""

import os
from pathlib import Path

# Share snapshots are HMAC-sealed — mirror the other suites' test secret.
os.environ.setdefault("SHARE_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
os.environ.setdefault("SHARE_SECRET_SKIP_BOOT_CHECK", "1")

REPO = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------
# legal_engine — escrow must accept every bids shape (the crash)
# ------------------------------------------------------------------
def test_escrow_dict_shaped_bids_no_crash():
    """Res['bids'] is a dict keyed by finding key — iterating it yields STRINGS."""
    from engines.legal_engine import generate_escrow_holdback_agreement

    out = generate_escrow_holdback_agreement(
        {"address": "1 Main", "city": "Austin", "state": "TX", "zip_code": "78701"},
        high_risk_findings=[
            {
                "id": "f001",
                "key": "f001",
                "description": "Heat exchanger cracked; furnace shut down",
                "system_category": "HVAC",
                "severity": "CRITICAL",
                "estimated_cost_avg": 2200,
            }
        ],
        contractor_bids={"f001": {"bid_amount": 2200, "contractor": "ABC HVAC"}},
    )
    items = out.get("holdback_items") or out.get("items") or []
    assert items, out.keys()
    assert all(isinstance(i, dict) for i in items)
    assert items[0]["holdback_amount"] == 2200 * 1.5
    assert out["total_holdback"] == 2200 * 1.5


def test_escrow_list_bids_and_garbage_rows():
    from engines.legal_engine import generate_escrow_holdback_agreement

    findings = [
        {
            "id": "f002",
            "key": "f002",
            "description": "Chimney step flashing rusted, shingles cracked",
            "system_category": "ROOF",
            "severity": "HIGH",
            "estimated_cost_avg": 1525,
        }
    ]
    out = generate_escrow_holdback_agreement(
        {"address": "2 Main"},
        high_risk_findings=findings,
        # dict-keyed garbage + list rows + plain strings must all survive
        contractor_bids={
            "f002": [
                {"bid_amount": 1525},
                "not-a-dict",
                {"garbage": True},
            ]
        },
    )
    items = out.get("holdback_items") or out.get("items") or []
    assert items
    assert items[0]["holdback_amount"] == round(1525 * 1.5), "holdback = 1.5x best bid, rounded"


# ------------------------------------------------------------------
# parser_engine — sample report: 5 real defects, no report chrome
# ------------------------------------------------------------------
def _sample_findings():
    import io

    from engines.parser_engine import process_uploaded_report
    from engines.sample_data import inspection_pdf_bytes

    return process_uploaded_report(io.BytesIO(inspection_pdf_bytes()))["findings"]


def test_parser_sample_report_quality():
    findings = _sample_findings()
    assert 5 <= len(findings) <= 15, f"expected ~10 real findings, got {len(findings)}"
    valid_sev = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
    for f in findings:
        desc = f["description"]
        assert f["severity"] in valid_sev, desc
        assert f.get("id") and f.get("key"), "stable ids required for bid/legal joins"
        assert "<" not in desc and ">" not in desc, f"HTML leaked: {desc[:80]}"
        assert not desc[0].islower(), f"fragment leaked: {desc[:80]}"
        assert "FINDINGS SUMMARY" not in desc and "\nItem" not in desc, desc[:80]
        assert f["system_category"] not in ("", None), desc[:80]
    descs = [f["description"].lower() for f in findings]
    assert not any("inspector signature" in d for d in descs)
    assert not any("report no." in d for d in descs)


def test_parser_classification_spot_checks():
    findings = _sample_findings()

    def system_of(*fragments):
        for f in findings:
            if all(fr in f["description"] for fr in fragments):
                return f["system_category"], f["severity"]
        return None, None

    sysname, sev = system_of("GFCI-protected")
    assert sysname == "ELECTRICAL", f"GFCI misfiled: {sysname}"
    sysname, sev = system_of("chimney step flashing")
    assert sysname == "ROOF", f"chimney misfiled: {sysname}"
    sysname, sev = system_of("heat exchanger")
    assert sev == "CRITICAL", f"heat exchanger severity: {sev}"


def test_parser_noise_and_header_guards():
    from engines.parser_engine import _is_noise_finding, _is_section_header_line

    blob = "FINDINGS SUMMARY\nItem\nSystem\nSeverity\nLocation\nRecommended action\nHeat exchanger cracked"
    assert _is_noise_finding(blob), "flattened summary-table blob must be noise"
    assert _is_noise_finding("The following items were photographed for documentation: attic hatch")
    assert _is_section_header_line("2. ROOFING & CHIMNEY")
    assert _is_section_header_line("HEATING & COOLING (HVAC)")
    assert not _is_section_header_line("Re-flash and seal; roofing repair"), "prose is not a header"
    assert not _is_section_header_line("Replace furnace, CO test before close")


def test_cross_source_dedupe_and_session_ids():
    """PDF + audio restatements collapse, then every survivor gets a stable id."""
    from engines.ingestion_engine import _dedupe
    from engines.parser_engine import assign_finding_ids

    a = {"description": "Active roof leak at chimney flashing; water staining on ceiling observed"}
    near_dup = {
        "description": "Active roof leak at chimney flashing; water staining on the ceiling observed in the upper bedroom"
    }
    distinct = {"description": "GFCI outlet missing at kitchen counter receptacle circuit"}
    out = _dedupe([a, near_dup, distinct])
    assert len(out) == 2, f"containment dedupe failed: {[f['description'][:40] for f in out]}"
    assign_finding_ids(out, prefix="f")
    ids = [f.get("id") for f in out]
    assert all(ids) and len(set(ids)) == len(ids)
    assert out[0].get("key") == out[0]["id"], "key must mirror id for bid/legal joins"


# ------------------------------------------------------------------
# UI/brand — severity chips, gradient tokens, Pixel font everywhere
# ------------------------------------------------------------------
def test_dtable_renders_severity_chips():
    src = (REPO / "app.py").read_text(encoding="utf-8")
    assert "_sev_chip" in src and "sev-chip" in src
    assert "render_financial_matrix" in src and "by_system" in src, "system rollup required"


def test_css_has_severity_tokens_and_gradient_metrics():
    css = (REPO / "static" / "style.css").read_text(encoding="utf-8")
    for token in ("--sev-critical", "--sev-high", "--sev-medium", "--sev-low", "--sev-info", "--brand-grad"):
        assert token in css, f"missing {token}"
    assert '[data-testid="stMetric"]::before' in css, "gradient metric accent required"
    assert ".sev-chip" in css
    assert "'Google Sans Flex'" in css


def test_swagger_brand_css_served():
    from fastapi.testclient import TestClient

    import api_server

    client = TestClient(api_server.app)
    r = client.get("/static/ui.css")
    assert r.status_code == 200 and "Google Sans Flex" in r.text
    docs = client.get("/")
    assert docs.status_code == 200 and "customCssUrl" in docs.text
    f = client.get("/static/fonts/GoogleSansFlex-VF.woff2")
    assert f.status_code == 200 and len(f.content) > 50000
    assert client.get("/static/fonts/../api_server.py").status_code == 404, "traversal must 404"


def test_share_portal_enterprise_brand():
    from fastapi.testclient import TestClient

    import api_server
    from engines.share_engine import seal_snapshot

    token = seal_snapshot(
        {
            "estimate_id": "est-test",
            "generated_at": "2026-10-24T00:00:00Z",
            "totals": {"total_avg": 25000, "total_low": 21000, "total_high": 30000},
            "rooms": [
                {"room": "Kitchen", "condition": "Fair", "priority": "HIGH", "low": 4000, "high": 6500},
                {
                    "room": "<script>alert(1)</script>",
                    "condition": "Good",
                    "priority": "LOW",
                    "low": 1,
                    "high": 2,
                },
            ],
        }
    )
    client = TestClient(api_server.app)
    r = client.get(f"/s/{token}")
    assert r.status_code == 200
    assert "Google Sans Flex" in r.text, "share portal must use Pixel font"
    assert "kpis" in r.text and "prefers-color-scheme" in r.text, "enterprise shell required"
    assert "&lt;script&gt;" in r.text and "<script>alert" not in r.text, "XSS escaped"
    assert "noindex" in r.text


# ------------------------------------------------------------------
# Exports — embedded Google Sans Flex + Excel styling
# ------------------------------------------------------------------
def test_pdf_embeds_google_sans_flex():
    from engines.export_pdf import _FONT_DIR, build_pdf_package

    assert (_FONT_DIR / "GoogleSansFlex-Regular.ttf").is_file()
    assert (_FONT_DIR / "GoogleSansFlex-Bold.ttf").is_file()
    b = build_pdf_package(
        {"total_avg": 12500, "total_low": 9000, "total_high": 17000},
        [
            {
                "severity": "HIGH",
                "system": "ROOF",
                "finding": "Active leak - flashing failed",
                "contractor_low": 8000,
                "contractor_high": 12000,
                "provenance": "MODELED",
            },
            {
                "severity": "CRITICAL",
                "system": "HVAC",
                "finding": "Heat exchanger cracked; furnace shut down",
                "contractor_low": 2000,
                "contractor_high": 3000,
                "provenance": "VERIFIED",
            },
        ],
    )
    assert b[:5] == b"%PDF-"
    assert b"GoogleSansFlex" in b, "brand font must be embedded"


def test_excel_enterprise_styling():
    import io

    from openpyxl import load_workbook

    from engines.export_excel import build_excel_workbook

    raw = build_excel_workbook(
        [
            {
                "system": "ROOF",
                "severity": "HIGH",
                "finding": "Leak",
                "contractor_low": 8000,
                "contractor_high": 12000,
                "provenance": "MODELED",
            }
        ],
        rooms=[
            {
                "room": "Kitchen",
                "condition": "Fair",
                "priority": "HIGH",
                "low": 1,
                "mid": 2,
                "high": 3,
                "top_issue": "Leak",
            }
        ],
    )
    wb = load_workbook(io.BytesIO(raw))
    ws = wb["Line items"]
    assert ws["A1"].fill.fgColor.rgb.endswith("0071E3"), "brand header fill required"
    assert ws.freeze_panes == "A2", "freeze panes required"
    assert ws["B2"].fill.fgColor.rgb.endswith("FDE7D3"), "severity fill required"
    assert "$" in ws["D2"].number_format
