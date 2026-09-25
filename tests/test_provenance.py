"""Enterprise guardrails: no simulate-language, 5-badge contract, no hard paths."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANON = {"VERIFIED", "USER_PROVIDED", "MODELED", "REQUIRES_KEY", "UNAVAILABLE"}


def test_no_hardcoded_windows_path():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert r"C:\realestate_repair_cost_estimator" not in app
    assert "sys.path.insert" not in app or "_REPO_ROOT" in app


def test_no_iframe_theme_hack():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "st.iframe(" not in app
    assert "window.parent.document;" not in app
    assert "d.documentElement.classList" not in app


def test_no_simulate_language_in_new_code():
    bad = []
    for p in list((ROOT / "engines").glob("*.py")) + [ROOT / "app.py"]:
        t = p.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(t.splitlines(), 1):
            low = line.lower()
            if (
                "simulate_contractor_bids(" in line
                and "def simulate_contractor_bids" not in line
                and "deprecated" not in low
                and "alias" not in low
            ):
                bad.append(f"{p.name}:{i}:{line.strip()}")
            if (
                "simulate_permit_check(" in line
                and "def simulate_permit_check" not in line
                and "deprecated" not in low
                and "alias" not in low
            ):
                bad.append(f"{p.name}:{i}:{line.strip()}")
    assert not bad, f"simulate-language calls remain: {bad[:10]}"


def test_canonical_badge_contract():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "BADGE_ALIASES" in app
    for b in CANON:
        assert b in app


def test_contractor_rename():
    from engines.contractor_engine import estimate_market_baseline, simulate_contractor_bids

    assert callable(estimate_market_baseline) and callable(simulate_contractor_bids)


def test_permit_rename():
    from engines.permit_engine import check_permit_compliance, simulate_permit_check

    assert callable(check_permit_compliance) and callable(simulate_permit_check)


def test_config_versioned():
    import json

    v = json.loads((ROOT / "data" / "config_version.json").read_text(encoding="utf-8"))
    assert "version" in v and "datasets" in v


def test_pixel_font_wired():
    css = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
    assert "Google Sans Flex" in css
    font = ROOT / "static" / "fonts" / "GoogleSansFlex-VF.woff2"
    assert font.exists() and font.stat().st_size > 50000


def test_no_canvas_tables():
    """Read-only tables must use theme-safe dtable(), not the canvas grid."""
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "st.dataframe(" not in app
    assert "st.data_editor(" not in app


def test_dtable_escapes_html():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "def dtable(" in src and "_html.escape" in src
