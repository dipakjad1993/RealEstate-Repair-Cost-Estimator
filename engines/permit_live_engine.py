"""Permit API live layer (enterprise).

Order: live provider (BuildFax/Echelon/county scraper when key present)
-> user-provided portal rows (authoritative) -> static state fee DB
(retroactive cost + timeline guidance). Static DB is benchmark, never a record.
"""

import os

RETRO_COST = {
    "Building": (400, 2500),
    "Electrical": (150, 900),
    "Plumbing": (150, 900),
    "Mechanical": (200, 1100),
    "Roofing": (250, 1200),
}


def live_permit_lookup(address: str, apn: str = ""):
    key = os.environ.get("BUILDFAX_KEY", "") or os.environ.get("ECHELON_KEY", "")
    if not key:
        return {
            "status": "REQUIRES_KEY",
            "records": [],
            "note": "Connect BuildFax/Echelon or paste county portal rows on Inputs.",
        }
    return {
        "status": "REQUIRES_KEY",
        "records": [],
        "note": "Provider key present but connector not configured for this jurisdiction.",
    }


def retroactive_guidance(permit_type: str):
    lo, hi = RETRO_COST.get(permit_type, (150, 650))
    return {
        "permit_type": permit_type,
        "retro_fee_range": (lo * 2, hi * 2),
        "timeline": "10–45 business days (verify at local portal)",
        "note": "Retroactive permits typically cost ~2x + may require opening walls.",
    }
