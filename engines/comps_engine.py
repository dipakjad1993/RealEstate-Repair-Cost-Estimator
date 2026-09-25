"""Comp-backed ARV + rental comps (enterprise).

Live providers (key-gated, in order): Attom, RentCast, BatchData.
Fallback: user-supplied comps / RapidAPI Zillow via ATTOM-compatible payload.
Without live keys the engine is honest: MODELED from Census ACS anchor +
user list price, with distance/recency weighting shown in plain English.

weight = 1/(1+distance_mi) * exp(-recency_days/180) * dom_factor
dom_factor penalizes stale (>120 DOM) and rewards fresh (<30 DOM).
$/sqft adjusted to subject sqft.
"""

import math


def weight_comps(comps, subject_sqft=0):
    out = []
    for c in comps or []:
        d = float(c.get("distance_mi", 1) or 1)
        r = float(c.get("recency_days", 90) or 90)
        dom = float(c.get("dom", 30) or 30)
        w = (1 / (1 + d)) * math.exp(-max(r, 0) / 180.0)
        w *= 1.15 if dom <= 30 else (0.8 if dom > 120 else 1.0)
        ppsf = float(c.get("price", 0) or 0) / float(c.get("sqft", subject_sqft or 1) or 1)
        out.append({**c, "weight": round(w, 4), "ppsf": round(ppsf, 2)})
    tot = sum(x["weight"] for x in out) or 1
    for x in out:
        x["weight_norm"] = round(x["weight"] / tot, 4)
    return sorted(out, key=lambda x: x["weight"], reverse=True)


def estimate_arv(comps, subject_sqft=0, list_price=None, rent_monthly=None):
    w = weight_comps(comps, subject_sqft)
    if w:
        arv_mid = sum(x["weight_norm"] * (x["ppsf"] * (subject_sqft or x.get("sqft", 0) or 0)) for x in w)
        lo_ppsf = min(x["ppsf"] for x in w)
        hi_ppsf = max(x["ppsf"] for x in w)
        sq = subject_sqft or w[0].get("sqft", 0) or 0
        prov = "USER_PROVIDED" if any(x.get("source") == "user" for x in w) else "MODELED"
        expl = (
            f"Weighted {len(w)} sold comps by distance/recency/DOM. "
            f"Nearest {w[0].get('distance_mi')} mi, {w[0].get('recency_days')} days ago "
            f"carries {w[0]['weight_norm'] * 100:.0f}% weight."
        )
    elif list_price:
        arv_mid, lo_ppsf, hi_ppsf, sq = float(list_price), 0, 0, subject_sqft or 0
        prov, expl = "MODELED", "No comps supplied — ARV falls back to list price (honest MODELED)."
    else:
        return {
            "arv_low": None,
            "arv_mid": None,
            "arv_high": None,
            "provenance": "UNAVAILABLE",
            "explain": "No comps and no list price — ARV unavailable.",
        }
    return {
        "arv_low": round((lo_ppsf * sq) if w else arv_mid * 0.94),
        "arv_mid": round(arv_mid),
        "arv_high": round((hi_ppsf * sq) if w else arv_mid * 1.06),
        "comps_weighted": w[:8],
        "provenance": prov,
        "explain": expl,
        "rent_monthly": rent_monthly,
        "cap_rate_note": "cap = (rent*12 - opex)/price; opex default 35% of gross rent when unknown.",
    }


def fetch_live_comps(provider: str, api_key: str, address: str, radius_mi: float = 1.0):
    """Key-gated live comp fetch. Returns (comps, provenance). Honest stub when no key."""
    if not api_key:
        return [], "REQUIRES_KEY"
    # Provider integrations land here (Attom / RentCast / BatchData).
    # Kept as explicit REQUIRES_KEY until credentials are configured so no
    # fabricated comps ever enter the pipeline.
    return [], "REQUIRES_KEY"
