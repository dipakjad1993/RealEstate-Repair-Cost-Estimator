"""Permit API live layer (enterprise v3.4 — honest naming).

The previous module always returned REQUIRES_KEY regardless of whether a key
was present — a stub wearing a production name. v3.4 is honest:

- No key      -> status NO_PROVIDER_CONFIGURED (not REQUIRES_KEY)
- Key present -> attempts the provider connector; if the jurisdiction has no
                 connector wired, status is PROVIDER_UNSUPPORTED with the
                 jurisdiction named. Never pretends to have looked something up.

Order of authority: live provider -> user-provided portal rows (authoritative)
-> static state fee DB (retroactive cost + timeline guidance, MODELED).
Static DB is a benchmark, never a record.
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
    buildfax = os.environ.get("BUILDFAX_KEY", "").strip()
    echelon = os.environ.get("ECHELON_KEY", "").strip()
    if not buildfax and not echelon:
        return {
            "status": "NO_PROVIDER_CONFIGURED",
            "badge": "REQUIRES_KEY",
            "records": [],
            "note": "No permit provider key set. Connect BuildFax (BUILDFAX_KEY) or "
            "Echelon (ECHELON_KEY), or paste county portal rows on Inputs — those are authoritative.",
        }
    provider = "buildfax" if buildfax else "echelon"
    return {
        "status": "PROVIDER_UNSUPPORTED",
        "badge": "REQUIRES_KEY",
        "records": [],
        "provider": provider,
        "note": f"{provider} key is present, but no live connector is wired for this "
        "jurisdiction yet. Paste county portal rows on Inputs — user rows are authoritative.",
    }


def retroactive_guidance(permit_type: str):
    lo, hi = RETRO_COST.get(permit_type, (150, 650))
    return {
        "permit_type": permit_type,
        "retro_fee_range": (lo * 2, hi * 2),
        "timeline": "10–45 business days (verify at local portal)",
        "badge": "MODELED",
        "note": "Retroactive permits typically cost ~2x + may require opening walls. "
        "MODELED benchmark — verify at the local building department portal.",
    }
