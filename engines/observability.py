"""Observability: structured JSON logs, badge-mix metrics, latency histograms.

North-Star product metric: VERIFIED% — the share of output figures carrying
the VERIFIED badge. If VERIFIED% drops, the product is lying. This module
tracks it per-estimate and exposes rolling aggregates for the health page
and Prometheus export (/metrics).

Structured logs are one JSON object per line (logfmt-compatible) with
estimate_id, provenance_badge_counts, and per-host latencies so any
log pipeline (Loki, Datadog, CloudWatch) can index them.

OpenTelemetry is optional: if opentelemetry-sdk is installed and
OTEL_EXPORTER_OTLP_ENDPOINT is set, spans are exported; otherwise the
API is a no-op so the deterministic core never depends on it.
"""

import json
import os
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timezone

VALID_BADGES = ("VERIFIED", "USER_PROVIDED", "MODELED", "REQUIRES_KEY", "UNAVAILABLE")

_lock = threading.Lock()
_badge_totals: dict[str, int] = defaultdict(int)
_estimate_count = 0
_recent_estimates: deque = deque(maxlen=500)
_host_latencies: dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
_engine_latencies: dict[str, deque] = defaultdict(lambda: deque(maxlen=200))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_json(event: str, **fields) -> None:
    """Emit one structured JSON log line to stdout (12-factor)."""
    record = {"ts": _now_iso(), "level": fields.pop("level", "INFO"), "event": event, **fields}
    print(json.dumps(record, default=str, separators=(",", ":")), flush=True)


def observe_badges(badge_counts: dict[str, int], estimate_id: str = "") -> None:
    """Record the badge mix for one estimate. Updates North-Star VERIFIED%."""
    global _estimate_count
    clean = {b: int(c) for b, c in (badge_counts or {}).items() if b in VALID_BADGES}
    with _lock:
        _estimate_count += 1
        for badge, count in clean.items():
            _badge_totals[badge] += count
        _recent_estimates.append({"estimate_id": estimate_id, "badges": clean, "ts": _now_iso()})
    total = sum(clean.values()) or 1
    log_json(
        "estimate.badge_mix",
        estimate_id=estimate_id,
        badge_counts=clean,
        verified_pct=round(clean.get("VERIFIED", 0) / total * 100, 2),
        total_figures=total,
    )


def observe_latency(host_or_engine: str, seconds: float, kind: str = "host") -> None:
    """Record one latency sample for a data host or engine stage."""
    bucket = _host_latencies if kind == "host" else _engine_latencies
    bucket[host_or_engine].append(float(seconds))


@contextmanager
def trace_span(name: str, **attrs):
    """OTel span if configured, else no-op context manager. Never raises."""
    otel_ok = False
    tracer = None
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        try:
            from opentelemetry import trace  # type: ignore

            tracer = trace.get_tracer("repair-estimator")
            otel_ok = True
        except Exception:
            otel_ok = False
    start = time.perf_counter()
    if otel_ok and tracer:
        with tracer.start_as_current_span(name) as span:
            for k, v in attrs.items():
                span.set_attribute(k, v)
            try:
                yield span
            finally:
                span.set_attribute("duration_ms", round((time.perf_counter() - start) * 1000, 2))
    else:
        try:
            yield None
        finally:
            pass
    observe_latency(name, time.perf_counter() - start, kind="engine")


def metrics_snapshot() -> dict:
    """Rolling aggregates for the health page and /metrics."""
    with _lock:
        badges = dict(_badge_totals)
        count = _estimate_count
        recent = list(_recent_estimates)
    total_badges = sum(badges.values()) or 1
    verified_pct = round(badges.get("VERIFIED", 0) / total_badges * 100, 2)
    recent_verified = []
    for est in recent[-100:]:
        tb = sum(est["badges"].values()) or 1
        recent_verified.append(est["badges"].get("VERIFIED", 0) / tb * 100)
    return {
        "total_estimates": count,
        "badge_totals": badges,
        "verified_pct_north_star": verified_pct,
        "verified_pct_last_100_mean": round(sum(recent_verified) / len(recent_verified), 2)
        if recent_verified
        else None,
        "host_p95_latency_ms": {h: _p95_ms(q) for h, q in _host_latencies.items()},
        "engine_p95_latency_ms": {e: _p95_ms(q) for e, q in _engine_latencies.items()},
        "generated_at": _now_iso(),
    }


def _p95_ms(samples) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    idx = min(len(ordered) - 1, int(len(ordered) * 0.95))
    return round(ordered[idx] * 1000, 2)


def prometheus_text() -> str:
    """Render current metrics in Prometheus exposition format."""
    snap = metrics_snapshot()
    lines = [
        "# HELP repair_estimator_estimates_total Total estimates processed.",
        "# TYPE repair_estimator_estimates_total counter",
        f"repair_estimator_estimates_total {snap['total_estimates']}",
        "# HELP repair_estimator_verified_pct North-Star VERIFIED badge share.",
        "# TYPE repair_estimator_verified_pct gauge",
        f"repair_estimator_verified_pct {snap['verified_pct_north_star']}",
    ]
    for badge, total in snap["badge_totals"].items():
        lines.append(f'repair_estimator_badge_total{{badge="{badge}"}} {total}')
    for host, p95 in (snap["host_p95_latency_ms"] or {}).items():
        if p95 is not None:
            lines.append(f'repair_estimator_host_p95_ms{{host="{host}"}} {p95}')
    return "\n".join(lines) + "\n"
