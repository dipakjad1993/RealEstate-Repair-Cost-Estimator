"""Deterministic engine tests — no network (mocked), no randomness."""

from engines.climate_engine_v2 import assess_climate_v2
from engines.comps_engine import estimate_arv, weight_comps
from engines.contractor_engine import estimate_market_baseline
from engines.negotiation_copilot import draft_offer_credit
from engines.pii_vault import redact_pii
from engines.rate_limit import RateLimiter
from engines.room_engine import rate_rooms
from engines.voice_nlp import link_transcript_to_findings


def test_baseline_prefers_user_quote():
    findings = [
        {"key": "k1", "description": "Panel upgrade", "system_category": "ELECTRICAL", "severity": "HIGH"}
    ]
    cm = {
        "line_items": [
            {"finding_key": "k1", "finding": "Panel upgrade", "total_low": 1000, "total_high": 2000}
        ]
    }
    quotes = [
        {
            "finding_key": "k1",
            "contractor": "Acme Elec",
            "license": "CA-1",
            "low": "900",
            "high": "1400",
            "eta_days": "3",
        }
    ]
    out = estimate_market_baseline(findings, "90210", cm, "CA", quotes)
    assert out["k1"]["cost_source"] == "USER_QUOTE"
    assert out["k1"]["bid_low"] == 900


def test_baseline_without_quote_is_deterministic():
    findings = [{"key": "k1", "description": "Fix roof", "system_category": "ROOF", "severity": "HIGH"}]
    cm = {"line_items": [{"finding_key": "k1", "finding": "Fix roof", "total_low": 1000, "total_high": 2000}]}
    a = estimate_market_baseline(findings, "90210", cm, "CA", [])
    b = estimate_market_baseline(findings, "90210", cm, "CA", [])
    assert a == b
    assert "[AWAITING BID]" in a["k1"]["contractor"]


def test_rooms_rate():
    findings = [
        {
            "description": "GFCI missing in kitchen",
            "severity": "HIGH",
            "system_category": "ELECTRICAL",
            "location": "Kitchen",
        },
        {
            "description": "Peeling paint",
            "severity": "LOW",
            "system_category": "EXTERIOR",
            "location": "Kitchen",
        },
    ]
    rooms = rate_rooms(findings)
    k = next(r for r in rooms if r["room"] == "Kitchen")
    assert k["condition"] in ("Good", "Fair", "Poor", "Gut")
    assert k["priority"] in ("Immediate (<30d)", "6-mo", "12-mo", "Deferred")
    assert k["low"] <= k["mid"] <= k["high"]


def test_comps_weighting():
    comps = [
        {"price": 500000, "sqft": 1500, "distance_mi": 0.2, "recency_days": 10, "dom": 12},
        {"price": 900000, "sqft": 1500, "distance_mi": 5.0, "recency_days": 300, "dom": 200},
    ]
    w = weight_comps(comps, subject_sqft=1500)
    assert w[0]["weight"] > w[1]["weight"]
    arv = estimate_arv(comps, subject_sqft=1500, list_price=520000)
    assert arv["arv_mid"] > 0 and arv["provenance"] in ("VERIFIED", "USER_PROVIDED", "MODELED", "UNAVAILABLE")


def test_climate_v2_deterministic():
    a = assess_climate_v2("CA", 34.0, -118.2, {"wildfire": 1, "foundation": 0})
    b = assess_climate_v2("CA", 34.0, -118.2, {"wildfire": 1, "foundation": 0})
    assert a == b
    assert "non_renewal_risk" in a and "premium_impact" in a


def test_negotiation_copilot_cites():
    out = draft_offer_credit(
        [{"system": "ROOF", "severity": "CRITICAL", "finding": "Active leak", "bid_high": 8000}],
        leverage=70,
        dom=90,
    )
    assert "credit" in out["letter"].lower()
    assert out["leverage"] == 70
    assert out["citations"]


def test_voice_nlp_links():
    findings = [{"description": "Cracked heat exchanger in furnace", "system_category": "HVAC"}]
    linked = link_transcript_to_findings("The furnace heat exchanger is cracked and unsafe", findings)
    assert linked[0]["linked_findings"]


def test_pii_redaction():
    s = "Contact at 1234 Maple Ave, Beverly Hills CA 90210, APN 44-33-12, phone 310-555-0142"
    r = redact_pii(s)
    assert "90210" not in r and "310-555-0142" not in r


def test_rate_limiter():
    rl = RateLimiter(max_calls=2, window_s=60)
    assert rl.allow("u1") and rl.allow("u1") and not rl.allow("u1")
