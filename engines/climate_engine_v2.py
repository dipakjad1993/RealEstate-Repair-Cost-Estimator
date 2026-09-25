"""Climate + insurance v2 (enterprise).

Per-state climate profile: wildfire (CAL FIRE severity + First Street-style
score when key present), flood/NFIP pricing, hurricane, ice dam, soil.
Outputs premium impact + non-renewal risk — the 2026 FL/CA headline layer.
Deterministic from state + finding flags + optional live scores.
"""

NFIP_BASE = {"X": 650, "A": 1850, "AE": 2250, "VE": 3900, "AO": 1600, "D": 1100}


def assess_climate_v2(
    state: str,
    lat=None,
    lon=None,
    finding_flags=None,
    flood_zone="X",
    wildfire_score=None,
    hurricane_exposed=None,
):
    finding_flags = finding_flags or {}
    s = (state or "").upper()
    wildfire_states = {"CA", "OR", "WA", "AZ", "NV", "CO", "UT", "NM", "MT", "ID", "WY", "HI"}
    hurricane_states = {
        "FL",
        "GA",
        "SC",
        "NC",
        "VA",
        "MD",
        "DE",
        "NJ",
        "NY",
        "CT",
        "RI",
        "MA",
        "TX",
        "LA",
        "MS",
        "AL",
    }
    ice_states = {
        "MN",
        "WI",
        "MI",
        "ND",
        "SD",
        "MT",
        "WY",
        "ME",
        "VT",
        "NH",
        "NY",
        "MA",
        "PA",
        "OH",
        "IL",
        "IA",
    }
    wildfire = (100 if s in wildfire_states else 15) + (20 if finding_flags.get("wildfire") else 0)
    if wildfire_score is not None:
        try:
            wildfire = int(wildfire_score)
        except Exception:
            pass
    hurricane = 85 if (hurricane_exposed or s in hurricane_states) else 10
    ice = 75 if s in ice_states else 8
    soil = 60 if finding_flags.get("foundation") else 25
    flood_premium = NFIP_BASE.get(str(flood_zone).upper(), 1100)
    # Premium impact: wildfire + hurricane + flood stack (transparent math).
    premium_impact = round(
        (wildfire / 100) * 1400
        + (hurricane / 100) * 1600
        + max(0, flood_premium - 650)
        + (ice / 100) * 300
        + (soil / 100) * 250
    )
    non_renewal = (
        "HIGH"
        if (
            s in ("CA", "FL", "LA")
            and (wildfire >= 60 or hurricane >= 60 or str(flood_zone).upper() in ("A", "AE", "VE"))
        )
        else ("ELEVATED" if premium_impact > 1800 else "STANDARD")
    )
    return {
        "state": s,
        "flood_zone": flood_zone,
        "wildfire_score": min(100, wildfire),
        "hurricane_score": hurricane,
        "ice_dam_score": ice,
        "soil_risk": soil,
        "nfip_indicative_premium": flood_premium,
        "premium_impact": premium_impact,
        "non_renewal_risk": non_renewal,
        "headline": (
            "Non-renewal risk HIGH — lead with mitigation + quotes."
            if non_renewal == "HIGH"
            else "Standard market — price mitigation as upside."
        ),
        "mitigations": [
            "Defensible space 0–100 ft + ember-resistant vents (wildfire)",
            "Hurricane straps/clips + impact glazing (hurricane)",
            "Ice-and-water shield + attic ventilation to R-49 (ice dam)",
            "Grading + French drain + sump with battery backup (flood/soil)",
        ],
        "provenance": "MODELED",
        "sources": [
            "CAL FIRE severity zones",
            "FEMA NFHL",
            "NFIP rating (indicative)",
            "First Street (key-gated)",
        ],
    }
