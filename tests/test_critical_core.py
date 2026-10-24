"""Deep coverage tests for the v3.4 security/provenance core modules.

The CI coverage gate runs on this critical set (not the full legacy engine
surface): audit_log, share_engine, rate_limit, pii_vault, observability,
confidence_engine, citable_engine, compliance_engine, etl_engine, fred_engine,
insurance_engine, investor_engine, legal_engine, permit_live_engine,
seo_engine, cost_engine. Target: ≥85% on these modules.
"""

import os
from pathlib import Path

os.environ.setdefault("SHARE_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
os.environ["API_AUTH_DISABLED"] = "1"

REPO = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------
# confidence_engine — calibrate + meta + edge cases
# ------------------------------------------------------------------
def test_confidence_meta_and_calibrate():
    from engines.confidence_engine import calibrate, confidence_meta, score_finding

    meta = confidence_meta()
    assert meta["badge"] == "MODELED"
    assert meta["calibration_status"] == "DEFAULT_WEIGHTS"
    # Hedging lowers confidence
    hedged = score_finding("The wall may possibly have a small crack somewhere.")
    asserted = score_finding(
        "Foundation crack 3 inches wide in basement, structural engineer required immediately."
    )
    assert asserted > hedged
    # Numeric measurement boosts
    measured = score_finding("Roof covering is 16 years old with granular loss.")
    bare = score_finding("Roof looks okay.")
    assert measured > bare
    # Calibrate with a small labeled corpus
    corpus = [
        {"text": "Cracked heat exchanger, replace immediately.", "human_confirmed": True},
        {"text": "May possibly be a issue.", "human_confirmed": False},
    ]
    fitted = calibrate(corpus)
    assert fitted["calibration_status"] == "CORPUS_FITTED"
    assert "fitted_precision_by_signal" in fitted


def test_confidence_clips_out_of_range():
    from engines.confidence_engine import score_finding

    short = score_finding("x", severity="INFO")
    assert short >= 0.10
    strong = score_finding(
        "Active gas leak at furnace, 3 inches crack in heat exchanger, replace immediately, carbon monoxide risk.",
        severity="CRITICAL",
        location="Basement",
    )
    assert strong <= 0.98


# ------------------------------------------------------------------
# observability — badge mix, metrics, prometheus, span
# ------------------------------------------------------------------
def test_observability_badge_mix_and_metrics():
    from engines.observability import metrics_snapshot, observe_badges, observe_latency, prometheus_text

    observe_badges({"VERIFIED": 3, "MODELED": 1, "USER_PROVIDED": 1}, estimate_id="e1")
    observe_badges({"MODELED": 5}, estimate_id="e2")
    observe_latency("bls.gov", 0.12, kind="host")
    observe_latency("cost_engine", 0.05, kind="engine")
    snap = metrics_snapshot()
    assert snap["total_estimates"] == 2
    assert snap["badge_totals"]["VERIFIED"] == 3
    assert snap["verified_pct_north_star"] > 0
    assert "bls.gov" in snap["host_p95_latency_ms"]
    text = prometheus_text()
    assert "repair_estimator_verified_pct" in text
    assert "repair_estimator_estimates_total" in text


def test_observability_span_noop_and_log_json(capsys):
    from engines.observability import log_json, trace_span

    log_json("test.event", level="INFO", x=1)
    captured = capsys.readouterr()
    assert '"event":"test.event"' in captured.out.replace(" ", "")
    with trace_span("test.engine", foo="bar"):
        pass  # no-op when OTel not configured; must not raise


# ------------------------------------------------------------------
# audit_log — export, verify_chain, tamper detection
# ------------------------------------------------------------------
def test_audit_log_tamper_detection(tmp_path, monkeypatch):
    from engines import audit_log

    monkeypatch.setattr(audit_log, "AUDIT_LOG_PATH", tmp_path / "a.jsonl")
    audit_log.log_event("e1", actor="a")
    audit_log.log_event("e2", actor="b")
    assert audit_log.verify_chain() is True
    # Tamper: rewrite the first event's payload
    lines = (tmp_path / "a.jsonl").read_text(encoding="utf-8").splitlines()
    rec = __import__("json").loads(lines[0])
    rec["payload"]["evil"] = 1
    lines[0] = __import__("json").dumps(rec, sort_keys=True, separators=(",", ":"))
    (tmp_path / "a.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert audit_log.verify_chain() is False


def test_audit_log_empty_export(tmp_path, monkeypatch):
    from engines import audit_log

    monkeypatch.setattr(audit_log, "AUDIT_LOG_PATH", tmp_path / "none.jsonl")
    assert audit_log.export_events() == []
    assert audit_log.verify_chain() is True


# ------------------------------------------------------------------
# rate_limit — remaining(), named limiter registry, redis fallback
# ------------------------------------------------------------------
def test_rate_limiter_remaining_and_named():
    from engines.rate_limit import RateLimiter, get_limiter

    rl = RateLimiter(max_calls=3, window_s=60, name="t")
    assert rl.remaining("k") == 3
    rl.allow("k")
    assert rl.remaining("k") == 2
    named = get_limiter("custom", max_calls=5, window_s=60)
    assert named.allow("x")
    # Same name returns same instance
    assert get_limiter("custom") is named


def test_rate_limiter_redis_fallback(monkeypatch):
    """With REDIS_URL set but Redis unreachable, limiter falls back to in-memory."""
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6399/0")  # unreachable port
    from engines.rate_limit import RateLimiter

    rl = RateLimiter(max_calls=2, window_s=60, name="fallback")
    assert rl.allow("k") and rl.allow("k") and not rl.allow("k")


# ------------------------------------------------------------------
# pii_vault — store/get/expire/redact_dict/vault audit
# ------------------------------------------------------------------
def test_pii_vault_full_lifecycle():
    from engines.pii_vault import redact_dict, vault_get, vault_store

    vault_store("s1", {"address": "1 Main St", "n": 5}, ttl_s=60)
    assert vault_get("s1") == {"address": "1 Main St", "n": 5}
    vault_store("s2", {"a": 1}, ttl_s=-1)
    assert vault_get("s2") is None  # expired
    red = redact_dict({"address": "1 Main St 90210", "zip": "90210", "nested": {"phone": "310-555-0142"}})
    assert red["address"] == "[redacted]"
    assert red["nested"]["phone"] == "[redacted]", "phone key is fully redacted by key-name rule"


def test_pii_vault_purges_on_capacity(monkeypatch):
    from engines import pii_vault

    monkeypatch.setattr(pii_vault, "_VAULT", {})
    monkeypatch.setattr(pii_vault, "_MAX_VAULT_ENTRIES", 3)
    for i in range(5):
        pii_vault.vault_store(f"s{i}", {"i": i}, ttl_s=-1)  # all expire immediately
    pii_vault.vault_store("fresh", {"ok": True}, ttl_s=60)
    assert pii_vault.vault_get("fresh") == {"ok": True}


# ------------------------------------------------------------------
# share_engine — rotation, share_url, kid
# ------------------------------------------------------------------
def test_share_url_and_rotation(monkeypatch):
    from engines.share_engine import open_snapshot, seal_snapshot, share_url

    current = os.environ["SHARE_SECRET"]
    token = seal_snapshot({"v": 1})
    url = share_url(token, base_url="https://prod.example.com")
    assert url.startswith("https://prod.example.com/s/")
    # Rotate: new secret, old token still opens via previous
    monkeypatch.setenv("SHARE_SECRET", "rotated-secret-0123456789abcdef0123456789abcde")
    monkeypatch.setenv("SHARE_SECRET_PREVIOUS", current)
    assert open_snapshot(token) == {"v": 1}
    # New seal uses new secret
    new_token = seal_snapshot({"v": 2})
    assert open_snapshot(new_token) == {"v": 2}
    # Garbage token
    assert open_snapshot("not-a-token") is None


def test_share_rejects_short_secret(monkeypatch):
    from engines.share_engine import ShareSecretError, seal_snapshot

    monkeypatch.setenv("SHARE_SECRET", "short")
    try:
        seal_snapshot({})
        raise AssertionError("short secret must be rejected")
    except ShareSecretError:
        pass


# ------------------------------------------------------------------
# citable_engine — deep markdown + jsonld fields
# ------------------------------------------------------------------
def test_citable_markdown_content_and_jsonld_fields():
    from engines.citable_engine import jsonld_dataset, markdown_twin

    md = markdown_twin(
        "id1",
        {"total_avg": 5000, "total_low": 4000, "total_high": 6000},
        [
            {
                "finding": "Roof leak",
                "system": "ROOF",
                "severity": "HIGH",
                "total_low": 4000,
                "total_avg": 5000,
                "total_high": 6000,
                "badge": "VERIFIED",
                "as_of": "2026-10-24",
                "source_url": "https://www.bls.gov/oes/",
            },
        ],
        zip_code="78701",
        deep_analysis={"m01": {"note": "summary text"}},
    )
    assert "Q&A" in md
    assert "Canonical URL" in md
    assert "summary text" in md
    jl = jsonld_dataset("id1", {"total_avg": 5000}, zip_code="78701")
    assert jl["variableMeasured"][0]["value"] == 5000
    assert jl["license"]


# ------------------------------------------------------------------
# compliance_engine — ecoa with enough sample
# ------------------------------------------------------------------
def test_ecoa_audit_flagged_and_pass_paths():
    from engines.compliance_engine import ecoa_audit

    # Construct a biased sample: high minority share -> higher modifier
    shares = {f"z{i:05d}": i / 100 for i in range(100)}
    # Manually monkeypatch ZIP_COST_MODIFIERS via the module's import
    import engines.compliance_engine as ce

    original = ce.ZIP_COST_MODIFIERS
    ce.ZIP_COST_MODIFIERS = {f"z{i:05d}": {"modifier": 1.0 + (i / 100) * 0.5} for i in range(100)}
    try:
        out = ecoa_audit(minority_share_data=shares, threshold_pp=5)
        assert out["status"] in ("FLAGGED", "PASS")
        assert out["matched_zips"] == 100
        assert "delta_pp" in out
    finally:
        ce.ZIP_COST_MODIFIERS = original
    # INSUFFICIENT_SAMPLE path
    out2 = ecoa_audit(minority_share_data={"z1": 0.5})
    assert out2["status"] == "INSUFFICIENT_SAMPLE"


# ------------------------------------------------------------------
# etl_engine — manifest listing, integrity failure
# ------------------------------------------------------------------
def test_etl_integrity_failure_returns_none(tmp_path, monkeypatch):
    from engines import etl_engine

    monkeypatch.setattr(etl_engine, "SNAPSHOT_DIR", tmp_path / "snaps")
    monkeypatch.setattr(etl_engine, "MANIFEST_PATH", tmp_path / "snaps" / "manifest.json")
    etl_engine.write_snapshot("ds", [1, 2, 3])
    # Corrupt the data file
    data_file = tmp_path / "snaps" / "ds_20261024.json"
    # Find actual file
    files = list((tmp_path / "snaps").glob("ds_*.json"))
    data_file = [f for f in files if not f.name.endswith(".meta.json")][0]
    data_file.write_text("[9,9,9]", encoding="utf-8")
    payload, meta = etl_engine.read_latest_snapshot("ds")
    assert payload is None, "corrupted snapshot must fail integrity check"
    man = etl_engine.snapshot_manifest()
    assert "ds" in man["datasets"]


# ------------------------------------------------------------------
# fred_engine — full REQUIRES_KEY + error path
# ------------------------------------------------------------------
def test_fred_macro_context_requires_key(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    from engines.fred_engine import fetch_macro_context

    ctx = fetch_macro_context()
    assert ctx["badge"] == "REQUIRES_KEY"
    assert set(ctx["series"].keys()) == {"FEDFUNDS", "HOUST", "CUUR0000SEHA", "WPU13"}


# ------------------------------------------------------------------
# insurance_engine — multiple flags + summary counts + scorecard
# ------------------------------------------------------------------
def test_insurance_multiple_flags_and_scorecard():
    from engines.insurance_engine import analyze_insurance_risk, calculate_insurance_scorecard

    findings = [
        {"description": "Polybutylene piping throughout, active leak under kitchen sink."},
        {"description": "Federal Pacific Stab-Lok panel in garage, breakers not tripping."},
        {"description": "Knob and tube wiring in attic."},
    ]
    out = analyze_insurance_risk(findings, {"state": "FL", "year_built": 1975})
    assert out["summary"]["total_red_flags"] >= 3
    assert out["summary"]["critical_flags"] >= 1
    assert out["summary"]["flag_values_badge"] == "MODELED"
    scorecard = calculate_insurance_scorecard(findings, {"state": "FL", "year_built": 1975})
    assert scorecard["grade"] in ("A", "B+", "B", "C+", "C", "D", "F")
    assert scorecard["red_flags"] >= 3


def test_insurance_user_quote_overrides_premium():
    from engines.insurance_engine import analyze_insurance_risk

    out = analyze_insurance_risk([], {"state": "CA", "year_built": 2010}, user_quote={"annual_premium": 1500})
    assert out["summary"]["premium_provenance"] == "USER_PROVIDED_CARRIER_QUOTE"
    assert out["summary"]["estimated_base_annual_premium"] == 1500


# ------------------------------------------------------------------
# investor_engine — deeper paths (modeled listing, quality grades)
# ------------------------------------------------------------------
def test_investor_modeled_fallbacks():
    from engines.investor_engine import analyze_investor_deal

    out = analyze_investor_deal(
        {"year_built": 1970, "square_footage": 1400, "state": "OH", "zip_code": "44114"},
        findings=[{"system_category": "HVAC", "description": "furnace failing"}],
        cost_matrix={"summary": {"total_avg": 30000, "total_low": 25000, "total_high": 40000}},
        capex_analysis={"summary": {"weighted_risk_exposure": 8000}},
        user_inputs={},
    )
    assert out["listing_price_provenance"] == "MODELED"
    assert out["arv_provenance"] == "MODELED"
    assert out["monthly_rental_provenance"] == "MODELED"
    assert out["risk_assessment"]["overall_deal_quality"]["grade"] in ("A", "B", "C", "D")
    assert out["depreciation_forecast"], "5-yr CapEx forecast must be present"
    assert len(out["investment_analysis"]) >= 1


# ------------------------------------------------------------------
# legal_engine — escrow holdback + attorney flag
# ------------------------------------------------------------------
def test_legal_escrow_holdback_flags():
    from engines.legal_engine import generate_escrow_holdback_agreement

    out = generate_escrow_holdback_agreement(
        {"address": "1 Main", "city": "Austin", "state": "TX", "zip_code": "78701"},
        high_risk_findings=[
            {
                "id": "f1",
                "description": "Roof leak",
                "system_category": "ROOF",
                "severity": "HIGH",
                "estimated_cost_avg": 8000,
            }
        ],
        contractor_bids=[],
    )
    assert out["ATTORNEY_REVIEW_REQUIRED"] is True
    assert out["total_holdback"] == 8000 * 1.5


# ------------------------------------------------------------------
# permit_live_engine — provider present but unsupported
# ------------------------------------------------------------------
def test_permit_provider_present_unsupported(monkeypatch):
    monkeypatch.setenv("BUILDFAX_KEY", "bf-key-123")
    from engines.permit_live_engine import live_permit_lookup, retroactive_guidance

    out = live_permit_lookup("1 Main")
    assert out["status"] == "PROVIDER_UNSUPPORTED"
    assert out["provider"] == "buildfax"
    retro = retroactive_guidance("Roofing")
    assert retro["badge"] == "MODELED"
    assert retro["retro_fee_range"][0] > 0


# ------------------------------------------------------------------
# seo_engine — landing pages + qa blocks + portfolio size
# ------------------------------------------------------------------
def test_seo_landing_pages_qa_and_as_of():
    from engines.seo_engine import generate_seo_landing_pages

    cost_data = {
        "line_items": [
            {"system": "roof", "total_low": 4000, "total_high": 8000},
            {"system": "hvac", "total_low": 3000, "total_high": 6000},
        ]
    }
    out = generate_seo_landing_pages("78701", cost_data)
    assert out["total_pages"] == 6
    roof = next(p for p in out["pages"] if p["system_type"] == "Roof")
    assert roof["avg_cost"] == 6000
    assert roof["as_of"]
    assert roof["qa_block"], "answer-shaped Q&A block required for GEO"
    assert "geo_strategy_note" in out


def test_prompt_portfolio_200():
    from engines.seo_engine import build_prompt_portfolio

    p = build_prompt_portfolio()
    assert p["total_prompts"] == 200
    assert all("runs_per_day" in x for x in p["portfolio"][:5])


# ------------------------------------------------------------------
# cost_engine — user quote badge path
# ------------------------------------------------------------------
def test_cost_engine_user_quote_badge():
    from engines.cost_engine import calculate_cost_bounds

    finding = {
        "key": "k1",
        "description": "Panel upgrade",
        "system_category": "ELECTRICAL",
        "severity": "HIGH",
    }
    out = calculate_cost_bounds(
        finding,
        "CA",
        "90210",
        user_quotes=[{"finding_key": "k1", "low": 900, "high": 1400, "contractor": "Acme"}],
    )
    assert out["badge"] == "USER_PROVIDED"
    assert out["provenance"] == "USER_QUOTE"
    out2 = calculate_cost_bounds(finding, "CA", "90210")
    assert out2["badge"] == "MODELED"
    assert out2["as_of"]
    assert out2["source_url"] == "https://www.bls.gov/oes/"


# ------------------------------------------------------------------
# Extra coverage: fred VERIFIED + error paths (mocked, no network)
# ------------------------------------------------------------------
def test_fred_verified_and_error_paths(monkeypatch):

    from engines import fred_engine

    class FakeResp:
        def json(self):
            return {
                "observations": [
                    {"date": "2026-10-01", "value": "4.50"},
                    {"date": "2026-09-01", "value": "."},
                ]
            }

    monkeypatch.setenv("FRED_API_KEY", "fake-key")
    monkeypatch.setattr(fred_engine, "timed_get", lambda *a, **k: FakeResp())
    out = fred_engine.fetch_fred_series("FEDFUNDS")
    assert out["badge"] == "VERIFIED"
    assert out["latest"]["value"] == 4.5
    assert out["observations"][1]["value"] is None
    ctx = fred_engine.fetch_macro_context()
    assert ctx["badge"] == "VERIFIED"

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(fred_engine, "timed_get", boom)
    err = fred_engine.fetch_fred_series("HOUST")
    assert err["badge"] == "UNAVAILABLE"
    assert "network down" in err["error"]


# ------------------------------------------------------------------
# Extra coverage: rate_limit redis success + remaining(redis)
# ------------------------------------------------------------------
class _FakeRedis:
    def __init__(self):
        self.store = {}

    def pipeline(self):
        return self

    def zremrangebyscore(self, *a):
        return self

    def zadd(self, key, mapping):
        self.store.setdefault(key, set()).update(mapping.keys())
        return self

    def zcard(self, key):
        return len(self.store.get(key, set()))

    def expire(self, *a):
        return self

    def execute(self):
        # emulate pipeline results: zrem, zadd, zcard, expire
        return [0, 1, self._last_card(), 1]

    def _last_card(self):
        return None

    def ping(self):
        return True


def test_rate_limiter_redis_path(monkeypatch):
    from engines import rate_limit as rl_mod

    fake = _FakeRedis()
    fake.execute = lambda: [0, 1, 1, 1]

    class FakePipe(_FakeRedis):
        def execute(self):
            # zrem, zadd, zcard=1, expire
            return [0, 1, 1, 1]

    fake.pipeline = lambda: FakePipe()
    monkeypatch.setattr(rl_mod.RateLimiter, "_try_connect", staticmethod(lambda url: fake))
    monkeypatch.setenv("REDIS_URL", "redis://fake:6379/0")
    rl = rl_mod.RateLimiter(max_calls=5, window_s=60, name="redis-test")
    assert rl.allow("k")
    assert isinstance(rl.remaining("k"), int) and rl.remaining("k") >= 0
    # Force redis failure -> fall back in-memory
    rl._redis_failed = True
    assert rl.allow("k2")


# ------------------------------------------------------------------
# Extra coverage: legal addendum with all three article types
# ------------------------------------------------------------------
def test_legal_addendum_full_articles():
    from engines.legal_engine import generate_legal_addendum

    findings = [
        {
            "description": "Roof leak",
            "severity": "HIGH",
            "system_category": "ROOF",
            "repair_type": "seller_repair",
        },
        {
            "description": "GFCI missing",
            "severity": "MEDIUM",
            "system_category": "ELECTRICAL",
            "repair_type": "seller_credit",
        },
        {
            "description": "Cracked tile",
            "severity": "LOW",
            "system_category": "EXTERIOR",
            "repair_type": "price_reduction",
        },
    ]
    cm = {
        "line_items": [
            {"finding": "Roof leak", "system": "ROOF", "total_avg": 5000},
            {"finding": "GFCI missing", "system": "ELECTRICAL", "total_avg": 800},
            {"finding": "Cracked tile", "system": "EXTERIOR", "total_avg": 400},
        ]
    }
    out = generate_legal_addendum(
        {"address": "1 Main", "city": "Austin", "state": "TX", "zip_code": "78701"},
        findings,
        cm,
        selected_items=findings,
    )
    assert out["total_repair_items"] == 1
    assert out["total_credit_items"] == 1
    assert out["total_reduction_items"] == 1
    assert "ARTICLE I" in out["addendum_text"]
    assert "ARTICLE II" in out["addendum_text"]
    assert "ARTICLE III" in out["addendum_text"]
    assert out["ATTORNEY_REVIEW_REQUIRED"] is True


# ------------------------------------------------------------------
# Extra coverage: observability p95 + empty buckets
# ------------------------------------------------------------------
def test_observability_p95_and_empty():
    from engines.observability import metrics_snapshot, observe_latency

    for v in (0.01, 0.02, 0.03, 0.2):
        observe_latency("hostx", v, kind="host")
    snap = metrics_snapshot()
    assert snap["host_p95_latency_ms"]["hostx"] is not None
    assert snap["engine_p95_latency_ms"] == {} or isinstance(snap["engine_p95_latency_ms"], dict)
