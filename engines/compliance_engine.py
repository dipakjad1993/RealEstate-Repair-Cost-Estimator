"""Compliance engine: EU AI Act documentation + ECOA/fair-lending adjacency audit.

This product produces repair-cost estimates that influence negotiations and
price. Two compliance surfaces matter:

1. EU AI Act (phase-ins 2025–2028). Insurance/financial-adjacent decisions
   are high-adjacent risk. This engine emits the required documentation
   artifacts: intended purpose, human-oversight path, training-data
   provenance (deterministic — none), post-market monitoring plan.

2. ECOA / fair-lending adjacency. ZIP-level cost modifiers can correlate
   with protected-class composition. `ecoa_audit()` runs a disparate-impact
   screen on zip_cost_modifiers against published minority-share data when
   supplied, and always returns the audit methodology so a finding is never
   hidden. Run before every enterprise deployment.
"""

from datetime import datetime, timezone
from typing import Any

from config import ZIP_COST_MODIFIERS

_AUDIT_AS_OF = datetime.now(timezone.utc).date().isoformat()


def eu_ai_act_documentation() -> dict:
    """Return the EU AI Act Art. 13/14/11 documentation pack for this system."""
    return {
        "system_name": "Real Estate Repair Cost Estimator",
        "system_version": _version(),
        "ai_act_classification": "High-adjacent (insurance/financial-adjacent decision support)",
        "intended_purpose": (
            "Deterministic repair-cost estimation and risk flagging for real estate "
            "transactions. Output supports — and never replaces — professional human "
            "judgment (appraisers, inspectors, underwriters, attorneys)."
        ),
        "human_oversight": {
            "path": "Every output is reviewed by a human operator before any decision.",
            "controls": [
                "Provenance badge on every figure (VERIFIED/USER_PROVIDED/MODELED/REQUIRES_KEY/UNAVAILABLE)",
                "ATTORNEY_REVIEW_REQUIRED hard-flag on all generated legal templates",
                "Deterministic core — no stochastic generation of numbers",
                "Audit log (append-only, hash-chained) on every estimate",
            ],
        },
        "training_data_provenance": (
            "NONE — this system is fully deterministic. No model training, no fine-tuning, "
            "no LLM-generated figures. Cost baselines derive from published government "
            "datasets (BLS OEWS/PPI, Census ACS, FEMA NFHL, USGS, CPSC) and versioned "
            "config tables. This is the strongest answer available under the AI Act."
        ),
        "post_market_monitoring": {
            "plan": (
                "Health endpoint tracks per-host latency and availability. "
                "Badge-mix metrics (VERIFIED% North Star) are exported to /metrics "
                "and alert on degradation. Gov-host outages page on-call via "
                "Prometheus/Grafana rules."
            ),
            "contact": "See repository SECURITY.md / GitHub Issues",
        },
        "risk_controls": [
            "Deterministic estimates — never 'simulated'",
            "Honest UNAVAILABLE badge when a source is unreachable (never guessed)",
            "USER_QUOTE always wins over baseline",
            "Rate limiting + auth on API surface",
            "PII redaction in logs; vaulted with TTL",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": _AUDIT_AS_OF,
    }


def ecoa_audit(
    minority_share_data: dict[str, float] | None = None,
    threshold_pp: float = 15.0,
) -> dict[str, Any]:
    """
    Disparate-impact screen on ZIP cost modifiers.

    minority_share_data: {zip_code: protected_class_share 0..1} from a
    published source (e.g. Census ACS B03002). When omitted, returns the
    methodology + modifier distribution so an auditor can supply data.

    Flags any ZIP where the mean cost modifier for ZIPs in the top vs bottom
    tercile of minority share differs by more than `threshold_pp` percentage
    points (the 80% rule / four-fifths rule adjacency screen).
    """
    modifiers = {
        z: float(v.get("modifier", 1.0)) for z, v in ZIP_COST_MODIFIERS.items() if isinstance(v, dict)
    }
    distribution = _describe(modifiers)
    result: dict[str, Any] = {
        "audit_type": "ECOA_disparate_impact_screen",
        "methodology": (
            "Compare mean ZIP cost modifier across terciles of protected-class share. "
            "Flag if top-tercile mean exceeds bottom-tercile mean by > threshold_pp "
            "(default 15pp). This is a SCREEN, not a legal determination."
        ),
        "threshold_pp": threshold_pp,
        "zip_count": len(modifiers),
        "modifier_distribution": distribution,
        "as_of": _AUDIT_AS_OF,
        "badge": "MODELED",
    }
    if not minority_share_data:
        result["status"] = "AWAITING_DATA"
        result["note"] = (
            "Supply minority_share_data={zip: share} from Census ACS B03002 to run the "
            "tercile comparison. Modifiers alone cannot establish disparate impact."
        )
        return result
    shares = {z: float(s) for z, s in minority_share_data.items() if z in modifiers}
    if len(shares) < 30:
        result["status"] = "INSUFFICIENT_SAMPLE"
        result["matched_zips"] = len(shares)
        result["note"] = "Need ≥30 matched ZIPs for a meaningful tercile screen."
        return result
    ordered = sorted(shares.items(), key=lambda kv: kv[1])
    n = len(ordered)
    tercile_size = n // 3
    bottom = [modifiers[z] for z, _ in ordered[:tercile_size]]
    top = [modifiers[z] for z, _ in ordered[-tercile_size:]]
    mean_bottom = sum(bottom) / len(bottom)
    mean_top = sum(top) / len(top)
    delta_pp = (mean_top / mean_bottom - 1) * 100 if mean_bottom else 0.0
    result.update(
        {
            "status": "FLAGGED" if delta_pp > threshold_pp else "PASS",
            "matched_zips": len(shares),
            "bottom_tercile_mean_modifier": round(mean_bottom, 4),
            "top_tercile_mean_modifier": round(mean_top, 4),
            "delta_pp": round(delta_pp, 2),
            "flagged": delta_pp > threshold_pp,
            "recommendation": (
                "Review ZIP modifier derivation for protected-class correlation. "
                "Modifiers should track construction labor + material cost, not demographics."
                if delta_pp > threshold_pp
                else "No disparate-impact signal above threshold in this screen."
            ),
        }
    )
    return result


def _describe(values: dict[str, float]) -> dict:
    if not values:
        return {}
    vals = sorted(values.values())
    n = len(vals)

    def pct(p):
        return round(vals[min(n - 1, int(n * p))], 4)

    return {
        "min": round(vals[0], 4),
        "p25": pct(0.25),
        "median": pct(0.5),
        "p75": pct(0.75),
        "max": round(vals[-1], 4),
        "mean": round(sum(vals) / n, 4),
    }


def _version() -> str:
    try:
        from config import config_version

        return config_version()
    except Exception:
        return "unknown"
