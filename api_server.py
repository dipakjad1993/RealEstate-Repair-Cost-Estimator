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
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
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
    docs_url="/",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "customCssUrl": "/static/ui.css",
        "persistAuthorization": True,
        "deepLinking": True,
    },
    contact={"name": "Dipak Jad", "url": "https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator"},
    license_info={"name": "MIT"},
)


# ------------------------------------------------------------------
# OWASP security headers (every response)
# ------------------------------------------------------------------
CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://cdn.jsdelivr.net; "
    "font-src 'self' data: https://cdn.jsdelivr.net; "
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
# Static brand assets (swagger skin + self-hosted Google Sans Flex)
# ------------------------------------------------------------------
STATIC_DIR = Path(__file__).resolve().parent / "static"
_ALLOWED_FONTS = {"GoogleSansFlex-VF.woff2", "Inter-VF.woff2"}


@app.get("/static/ui.css", include_in_schema=False)
def swagger_brand_css():
    css = STATIC_DIR / "swagger_brand.css"
    if not css.is_file():
        raise HTTPException(status_code=404, detail="stylesheet not found")
    return FileResponse(css, media_type="text/css; charset=utf-8")


@app.get("/static/fonts/{name}", include_in_schema=False)
def font_file(name: str):
    if name not in _ALLOWED_FONTS:
        raise HTTPException(status_code=404, detail="font not found")
    path = STATIC_DIR / "fonts" / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="font not found")
    media = "font/woff2"
    return FileResponse(path, media_type=media, headers={"Cache-Control": "public, max-age=86400"})


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


@app.get("/docs", include_in_schema=False)
def docs_redirect():
    """Swagger UI now lives at the site root — keep /docs working."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/", status_code=308)


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

    _prio_colors = {
        "CRITICAL": ("#DC2626", "rgba(220,38,38,.12)"),
        "HIGH": ("#EA580C", "rgba(234,88,12,.12)"),
        "MEDIUM": ("#CA8A04", "rgba(202,138,4,.12)"),
        "LOW": ("#16A34A", "rgba(22,163,74,.12)"),
        "INFO": ("#2563EB", "rgba(37,99,235,.12)"),
    }

    def _room_row(r):
        prio_raw = str(r.get("priority", "")).strip()
        prio_key = prio_raw.upper()
        color, bg = _prio_colors.get(prio_key, ("#6E6E73", "rgba(110,110,115,.10)"))
        chip_label = escape(str(r.get("priority", "")))
        chip_style = f"color:{color};background:{bg};border:1px solid {color}44"
        return (
            "<tr>"
            f"<td>{escape(str(r.get('room', '')))}</td>"
            f"<td>{escape(str(r.get('condition', '')))}</td>"
            f"<td><span class='prio' style='{chip_style}'>{chip_label}</span></td>"
            f"<td class='num'>${r.get('low', 0):,.0f}–${r.get('high', 0):,.0f}</td>"
            "</tr>"
        )

    rows = "".join(_room_row(r) for r in snap.get("rooms", []))
    estimate_id = escape(str(snap.get("estimate_id", "unknown")))
    generated = escape(str(snap.get("generated_at", "unknown")))
    room_count = len(snap.get("rooms", []))
    return (
        "<!doctype html><html lang='en'><head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<meta name='robots' content='noindex'>"
        "<title>Repair Estimate — Lender Package</title>"
        "<style>"
        "@font-face{font-family:'Google Sans Flex';font-style:normal;font-display:swap;"
        "font-weight:1 1000;font-stretch:75% 125%;"
        "src:url('/static/fonts/GoogleSansFlex-VF.woff2') format('woff2-variations')}"
        ":root{--bg:#f5f5f7;--surface:#fff;--ink:#1d1d1f;--ink2:#6e6e73;"
        "--line:rgba(0,0,0,.08);--accent:#0071E3;--grad:linear-gradient(90deg,#0071E3,#7C3AED)}"
        "@media(prefers-color-scheme:dark){:root{--bg:#000;--surface:#111114;--ink:#f5f5f7;"
        "--ink2:#98989d;--line:rgba(255,255,255,.14);"
        "--grad:linear-gradient(90deg,#0071E3,#7C3AED)}}"
        "*{box-sizing:border-box}"
        "body{margin:0;background:var(--bg);color:var(--ink);"
        "font-family:'Google Sans Flex','Google Sans','Inter',system-ui,-apple-system,sans-serif;"
        "-webkit-font-smoothing:antialiased}"
        "header{background:var(--grad);color:#fff;padding:30px 26px 44px}"
        "header h1{margin:0;font-size:1.4rem;letter-spacing:-.02em;font-weight:700}"
        "header p{margin:7px 0 0;opacity:.88;font-size:.85rem}"
        "main{max-width:880px;margin:0 auto;padding:0 20px 44px}"
        ".kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));"
        "gap:12px;margin-top:-28px}"
        ".kpi{background:var(--surface);border:1px solid var(--line);border-radius:16px;"
        "padding:14px 16px;box-shadow:0 8px 30px rgba(0,0,0,.10);position:relative;overflow:hidden}"
        ".kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;"
        "background:var(--grad)}"
        ".kpi .label{font-size:.66rem;text-transform:uppercase;letter-spacing:.07em;"
        "color:var(--ink2);font-weight:700}"
        ".kpi .value{font-size:1.3rem;font-weight:700;letter-spacing:-.02em;margin-top:5px}"
        ".tablewrap{overflow-x:auto;background:var(--surface);border:1px solid var(--line);"
        "border-radius:16px;margin-top:22px}"
        "table{width:100%;border-collapse:collapse}"
        "caption{caption-side:top;text-align:left;font-weight:700;padding:14px 16px 0;"
        "font-size:.95rem;color:var(--ink)}"
        "th{font-size:.66rem;text-transform:uppercase;letter-spacing:.06em;color:var(--ink2);"
        "text-align:left;padding:12px 16px 8px;border-bottom:1px solid var(--line);font-weight:700}"
        "td{padding:11px 16px;border-bottom:1px solid var(--line);font-size:.9rem}"
        "tr:last-child td{border-bottom:none}"
        "tbody tr:hover td{background:rgba(0,113,227,.05)}"
        ".num{font-variant-numeric:tabular-nums;white-space:nowrap;text-align:right}"
        ".prio{display:inline-block;font-size:.68rem;font-weight:700;letter-spacing:.05em;"
        "padding:.16rem .6rem;border-radius:999px;white-space:nowrap}"
        "footer{color:var(--ink2);font-size:.78rem;margin-top:24px;line-height:1.65}"
        "@media print{header{-webkit-print-color-adjust:exact;print-color-adjust:exact}}"
        "</style></head><body>"
        "<header><h1>Repair Estimate — Lender Package</h1>"
        "<p>Provenance-tracked · deterministic · not a quote</p></header><main>"
        "<div class='kpis'>"
        f"<div class='kpi'><div class='label'>Total (avg)</div>"
        f"<div class='value'>${totals.get('total_avg', 0):,.0f}</div></div>"
        f"<div class='kpi'><div class='label'>Range</div>"
        f"<div class='value'>${totals.get('total_low', 0):,.0f}–${totals.get('total_high', 0):,.0f}</div></div>"
        f"<div class='kpi'><div class='label'>Rooms</div><div class='value'>{room_count}</div></div>"
        "</div>"
        "<div class='tablewrap'><table>"
        "<caption>Room-by-room repair ranges</caption>"
        "<thead><tr><th>Room</th><th>Condition</th><th>Priority</th>"
        "<th class='num'>Range</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
        "<footer>Provenance: VERIFIED baselines + MODELED assembly. Not a quote.<br>"
        f"estimate_id: {estimate_id} · generated_at: {generated}<br>"
        "badge legend: VERIFIED · USER_PROVIDED · MODELED · REQUIRES_KEY · UNAVAILABLE"
        "</footer></body></html>"
    )


# Keep the ASGI module importable as `app` for uvicorn.
# The module-level name is required by `uvicorn api_server:app`.
