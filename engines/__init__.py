"""Engine package — explicit re-exports (no star imports, ruff-clean).

The previous star-import surface (22 modules re-exported via wildcard)
hid the dependency graph, slowed cold starts, and broke static analysis.
Every engine is now imported explicitly by module path at the call site.
This file only re-exports the small public surface other packages rely on.
"""

from engines.audit_log import export_events, log_event, verify_chain
from engines.capex_engine import generate_capex_horizon
from engines.comps_engine import estimate_arv, weight_comps
from engines.contractor_engine import estimate_market_baseline, get_contractor_recommendations
from engines.cost_engine import RealRates, calculate_cost_bounds, generate_cost_matrix
from engines.depreciation_engine import calculate_depreciation_curve
from engines.insurance_engine import analyze_insurance_risk, calculate_insurance_scorecard
from engines.investor_engine import analyze_investor_deal
from engines.legal_engine import generate_escrow_holdback_agreement, generate_legal_addendum
from engines.market_engine import generate_market_profile
from engines.observability import log_json, metrics_snapshot, observe_badges, trace_span
from engines.permit_engine import check_permit_compliance
from engines.pii_vault import redact_dict, redact_pii, vault_get, vault_store
from engines.rate_limit import GLOBAL_LIMITER, RateLimiter, get_limiter
from engines.room_engine import rate_rooms
from engines.seo_engine import generate_seo_landing_pages
from engines.share_engine import open_snapshot, seal_snapshot, share_url

__all__ = [
    "analyze_investor_deal",
    "analyze_insurance_risk",
    "calculate_cost_bounds",
    "calculate_depreciation_curve",
    "calculate_insurance_scorecard",
    "check_permit_compliance",
    "estimate_arv",
    "estimate_market_baseline",
    "export_events",
    "generate_capex_horizon",
    "generate_cost_matrix",
    "generate_escrow_holdback_agreement",
    "generate_legal_addendum",
    "generate_market_profile",
    "generate_seo_landing_pages",
    "get_contractor_recommendations",
    "get_limiter",
    "log_event",
    "log_json",
    "metrics_snapshot",
    "observe_badges",
    "open_snapshot",
    "rate_rooms",
    "RealRates",
    "redact_dict",
    "redact_pii",
    "RateLimiter",
    "seal_snapshot",
    "share_url",
    "trace_span",
    "vault_get",
    "vault_store",
    "verify_chain",
    "weight_comps",
    "GLOBAL_LIMITER",
]
