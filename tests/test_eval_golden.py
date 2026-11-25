"""Golden-set eval harness — regression contract on the inspection fixture.

Run: pytest tests/test_eval_golden.py -q
The golden fixture is generated deterministically by engines.sample_data, so
this harness needs no checked-in PDF and no network access.
"""

import io

from engines.parser_engine import process_uploaded_report
from engines.sample_data import inspection_pdf_bytes


def _parse():
    return process_uploaded_report(io.BytesIO(inspection_pdf_bytes()))


def test_golden_inspection_findings():
    r = _parse()
    findings = r["findings"]
    assert r["total_pages"] >= 1
    assert len(findings) == 10, f"golden finding count drifted: {len(findings)}"
    first = findings[0]
    assert first["severity"] == "CRITICAL"
    assert first["system_category"] == "HVAC"
    assert "heat exchanger" in first["subsystem"]
    assert "carbon monoxide" in first["description"].lower()


def test_golden_parse_is_deterministic():
    a, b = _parse(), _parse()
    assert [f["description"] for f in a["findings"]] == [f["description"] for f in b["findings"]]
    assert [f["severity"] for f in a["findings"]] == [f["severity"] for f in b["findings"]]


def test_golden_cost_matrix_badges_and_totals():
    from engines.cost_engine import generate_cost_matrix

    findings = _parse()["findings"]
    cm = generate_cost_matrix(findings, "CA", "90001", [], None)
    items = cm["line_items"]
    assert len(items) == len(findings)
    for it in items:
        assert it["badge"] in ("MODELED", "USER_PROVIDED")
        assert it["as_of"]
        assert it["source_url"]
        assert 0 <= it["total_low"] <= it["total_avg"] <= it["total_high"]
        assert it["geo_factor"] > 0
    assert cm["summary"]["total_avg"] > 0
