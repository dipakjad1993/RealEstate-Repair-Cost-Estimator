"""FastAPI backend: agent-ready estimate API + share portal + OpenAPI (enterprise v3.4).

Run:  uvicorn api_server:app --port 8000
Docs: /docs   OpenAPI: /v1/openapi.json   Share: /s/{token}   Metrics: /metrics

Enterprise hardening (v3.4):
- Timing-safe API-key auth (hmac.compare_digest). Auth is REQUIRED unless
  explicitly disabled with API_AUTH_DISABLED=1 (dev only).
- OWASP security headers (CSP, HSTS, X-Content-Type-Options, Referrer-Policy,
  X-Frame-Options) on every response.
- All dynamic HTML is escaped (share portal).
- Idempotency-Key support on POST /v1/estimate_repair (agents retry).
- Audit log on every estimate + share-token read (append-only, hash-chained).
- Per-figure as_of/source_url/retrieved_at in responses (citable).
- Named rate limiters per endpoint; Redis-backed when REDIS_URL is set.
- Structured JSON logs + badge-mix metrics (North-Star VERIFIED%).
"""

import hmac
import os
import uuid
from datetime import datetime, timezone
from html import escape
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from engines.audit_log import log_event
from engines.observability import log_json, metrics_snapshot, observe_badges, prometheus_text
from engines.pii_vault import redact_dict
from engines.rate_limit import get_limiter
from engines.share_engine import ShareSecretError, open_snapshot, seal_snapshot, validate_share_secret

API_KEY = os.environ.get("API_KEY", "").strip()
AUTH_DISABLED = os.environ.get("API_AUTH_DISABLED", "") == "1"

API_VERSION = "3.4.0"
IDEMPOTENCY_TTL_S = 24 * 3600
_idempotency_cache: dict[str, dict] = {}  # key -> {ts, response}

app = FastAPI(
    title="Repair Estimator API",
    version=API_VERSION,
    description=(
        "Provenance-tracked repair estimates. Every figure carries exactly one badge: "
        "VERIFIED / USER_PROVIDED / MODELED / REQUIRES_KEY / UNAVAILABLE. "
        "Deterministic — same inputs produce same outputs. Estimates, never simulations."
    ),
    openapi_url="/v1/openapi.json",
    docs_url="/docs",
    contact={"name": "Dipak Jad", "url": "https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator"},
    license_info={"name": "MIT"},
)


# ------------------------------------------------------------------
# OWASP security headers (every response)
# ------------------------------------------------------------------
CSP_POLICY = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Content-Security-Policy", CSP_POLICY)
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    if request.url.scheme == "https" or os.environ.get("FORCE_HSTS", "") == "1":
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
    response.headers.setdefault("X-Request-ID", request_id)
    return response


# ------------------------------------------------------------------
# Boot checks — fail fast on insecure production config
# ------------------------------------------------------------------
@app.on_event("startup")
def _boot_validate():
    if AUTH_DISABLED:
        log_json("boot.auth_disabled", level="WARNING", note="API_AUTH_DISABLED=1 — dev only")
        return
    if not API_KEY:
        log_json("boot.api_key_missing", level="WARNING", note="Set API_KEY or API_AUTH_DISABLED=1 for dev")
    try:
        validate_share_secret()
    except ShareSecretError as e:
        if os.environ.get("ALLOW_INSECURE_SHARE", "") == "1":
            log_json("boot.share_secret_insecure", level="ERROR", note=str(e))
        else:
            raise


# ------------------------------------------------------------------
# Auth — timing-safe
# ------------------------------------------------------------------
def _auth(authorization: str = ""):
    if AUTH_DISABLED:
        return "dev-anon"
    if not API_KEY:
        raise HTTPException(status_code=503, detail="server not configured: API_KEY unset")
    expected = f"Bearer {API_KEY}"
    if not hmac.compare_digest(authorization or "", expected):
        log_event("auth.failed", actor="unknown", payload={"prefix": (authorization or "")[:12]})
        raise HTTPException(status_code=401, detail="invalid API key")
    return "api-key"


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------
class EstimateRequest(BaseModel):
    address: str = ""
    city: str = ""
    state: str = Field(default="", max_length=2)
    zip_code: str = ""
    sqft: float = 1500
    year_built: int = 1995
    findings: list[dict[str, Any]] = []
    list_price: float | None = None
    comps: list[dict[str, Any]] = []


class FiguredResponse(JSONResponse):
    """JSON response that always includes provenance envelope."""


def _provenance_envelope(cm: dict, req_id: str) -> dict:
    """Per-figure provenance: as_of, source_url, retrieved_at, badge per line item."""
    now = datetime.now(timezone.utc).isoformat()
    line_items = []
    for it in cm.get("line_items", []):
        line_items.append(
            {
                **it,
                "badge": it.get("badge", "MODELED"),
                "as_of": it.get("as_of", now),
                "source_url": it.get("source_url", "https://www.bls.gov/oes/"),
                "retrieved_at": now,
            }
        )
    badge_counts: dict[str, int] = {}
    for it in line_items:
        badge_counts[it["badge"]] = badge_counts.get(it["badge"], 0) + 1
    return {
        "line_items": line_items,
        "badge_counts": badge_counts,
        "config_version": _config_version(),
        "generated_at": now,
        "estimate_id": req_id,
    }


def _config_version() -> str:
    try:
        import config

        return config.config_version()
    except Exception:
        return "unknown"


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.get("/v1/openapi.json")
def openapi_v1():
    return JSONResponse(app.openapi())


@app.get("/api/openapi.json")
def openapi_legacy():
    """Legacy alias — prefer /v1/openapi.json."""
    return JSONResponse(app.openapi())


@app.get("/llms.txt")
def llms_txt():
    return PlainTextResponse(
        "# Repair Estimator API\n"
        "> Deterministic, provenance-tracked repair estimates from verified government data.\n\n"
        "## Endpoints\n"
        "- POST /v1/estimate_repair {address, state, zip_code, findings[]}  (Authorization: Bearer <API_KEY>)\n"
        "- GET /s/{token} — lender share portal\n"
        "- GET /api/health — data-host health + latency\n"
        "- GET /metrics — Prometheus exposition (badge mix, VERIFIED%)\n\n"
        "## Provenance badges (exactly one per figure)\n"
        "VERIFIED · USER_PROVIDED · MODELED · REQUIRES_KEY · UNAVAILABLE\n\n"
        "## Rules\n"
        "- MODELED figures are deterministic estimates, not quotes.\n"
        "- USER_QUOTE rows are authoritative and always win.\n"
        "- Every figure carries as_of + source_url + retrieved_at.\n"
        "- Same inputs → same outputs. Estimates, never simulations.\n",
        media_type="text/plain",
    )


@app.get("/api/health")
def health():
    try:
        from engines.gov_sources_v2 import detailed_health

        h = detailed_health()
        h["api_version"] = API_VERSION
        h["metrics"] = metrics_snapshot()
        return h
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "api_version": API_VERSION}


@app.get("/metrics")
def metrics():
    return PlainTextResponse(prometheus_text(), media_type="text/plain; version=0.0.4")


def _run_estimate(req: EstimateRequest, req_id: str) -> dict:
    from engines.comps_engine import estimate_arv
    from engines.cost_engine import generate_cost_matrix
    from engines.room_engine import rate_rooms

    findings = [
        {
            "description": f.get("description", ""),
            "severity": f.get("severity", "MEDIUM"),
            "system_category": f.get("system", "OTHER"),
            "key": f.get("description", ""),
        }
        for f in req.findings
    ]
    cm = generate_cost_matrix(findings, req.state, req.zip_code, [], None)
    provenance = _provenance_envelope(cm, req_id)
    observe_badges(provenance["badge_counts"], estimate_id=req_id)
    cost_by = {
        it.get("finding_key", it.get("finding", "")): {
            "low": it.get("total_low", 0),
            "mid": it.get("total_avg", 0),
            "high": it.get("total_high", 0),
        }
        for it in cm.get("line_items", [])
    }
    rooms = rate_rooms(
        [
            {
                "description": f.get("description", ""),
                "severity": f.get("severity", "MEDIUM"),
                "system_category": f.get("system", "OTHER"),
                "location": f.get("room", "General"),
                "key": f.get("description", ""),
            }
            for f in req.findings
        ],
        cost_by,
    )
    arv = estimate_arv(req.comps, subject_sqft=req.sqft, list_price=req.list_price)
    try:
        token = seal_snapshot(
            redact_dict(
                {
                    "zip": req.zip_code,
                    "state": req.state,
                    "totals": cm.get("summary", {}),
                    "rooms": rooms,
                    "arv": arv,
                    "estimate_id": req_id,
                }
            )
        )
    except ShareSecretError:
        token = None
    log_event(
        "estimate.created",
        actor="api",
        payload={
            "estimate_id": req_id,
            "zip": req.zip_code,
            "state": req.state,
            "findings": len(req.findings),
        },
    )
    log_json(
        "estimate.completed",
        estimate_id=req_id,
        badge_counts=provenance["badge_counts"],
        findings=len(req.findings),
    )
    return {
        "totals": cm.get("summary", {}),
        "line_items": provenance["line_items"],
        "badge_counts": provenance["badge_counts"],
        "rooms": rooms,
        "arv": arv,
        "share_token": token,
        "provenance": "pipeline: VERIFIED baselines + MODELED assembly",
        "config_version": provenance["config_version"],
        "generated_at": provenance["generated_at"],
        "estimate_id": req_id,
    }


@app.post("/v1/estimate_repair")
def estimate_repair_v1(
    req: EstimateRequest,
    response: Response,
    authorization: str = Header(default=""),
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
):
    _auth(authorization)
    limiter = get_limiter("estimate", max_calls=60, window_s=60)
    if not limiter.allow(authorization or "anon"):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    now = datetime.now(timezone.utc).timestamp()
    if idempotency_key:
        cached = _idempotency_cache.get(idempotency_key)
        if cached and now - cached["ts"] < IDEMPOTENCY_TTL_S:
            response.headers["X-Idempotent-Replay"] = "true"
            return cached["response"]
    req_id = uuid.uuid4().hex[:16]
    result = _run_estimate(req, req_id)
    if idempotency_key:
        _idempotency_cache[idempotency_key] = {"ts": now, "response": result}
        if len(_idempotency_cache) > 10_000:
            for k in [k for k, v in _idempotency_cache.items() if now - v["ts"] >= IDEMPOTENCY_TTL_S][:1000]:
                _idempotency_cache.pop(k, None)
    return result


@app.post("/api/estimate_repair")
def estimate_repair_legacy(
    req: EstimateRequest,
    authorization: str = Header(default=""),
):
    """Legacy alias — prefer /v1/estimate_repair (adds idempotency + richer provenance)."""
    _auth(authorization)
    limiter = get_limiter("estimate", max_calls=60, window_s=60)
    if not limiter.allow(authorization or "anon"):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    req_id = uuid.uuid4().hex[:16]
    result = _run_estimate(req, req_id)
    return {
        "totals": result["totals"],
        "rooms": result["rooms"],
        "arv": result["arv"],
        "share_token": result["share_token"],
        "provenance": result["provenance"],
    }


@app.get("/s/{token}", response_class=HTMLResponse)
def share_portal(token: str):
    snap = open_snapshot(token)
    log_event("share.read", actor="portal", payload={"token_prefix": token[:12], "valid": bool(snap)})
    if not snap:
        raise HTTPException(status_code=404, detail="share link invalid or expired")
    totals = snap.get("totals") or {}
    rows = "".join(
        "<tr>"
        f"<td>{escape(str(r.get('room', '')))}</td>"
        f"<td>{escape(str(r.get('condition', '')))}</td>"
        f"<td>{escape(str(r.get('priority', '')))}</td>"
        f"<td>${r.get('low', 0):,.0f}–${r.get('high', 0):,.0f}</td>"
        "</tr>"
        for r in snap.get("rooms", [])
    )
    estimate_id = escape(str(snap.get("estimate_id", "unknown")))
    generated = escape(str(snap.get("generated_at", "unknown")))
    return (
        "<html><head><title>Lender package</title>"
        "<meta charset='utf-8'>"
        "<meta name='robots' content='noindex'>"
        "</head><body style='font-family:Inter,Arial'>"
        "<h1>Repair estimate — lender package</h1>"
        f"<p>Total avg ${totals.get('total_avg', 0):,.0f} · Range ${totals.get('total_low', 0):,.0f}–${totals.get('total_high', 0):,.0f}</p>"
        f"<table border=1 cellpadding=6><caption>Room-by-room repair ranges</caption>"
        f"<tr><th>Room</th><th>Condition</th><th>Priority</th><th>Range</th></tr>{rows}</table>"
        "<p>Provenance: VERIFIED baselines + MODELED assembly. Not a quote.</p>"
        f"<p><small>estimate_id: {estimate_id} · generated_at: {generated} · "
        "badge legend: VERIFIED · USER_PROVIDED · MODELED · REQUIRES_KEY · UNAVAILABLE</small></p>"
        "</body></html>"
    )


# Keep the ASGI module importable as `app` for uvicorn.
# The module-level name is required by `uvicorn api_server:app`.
