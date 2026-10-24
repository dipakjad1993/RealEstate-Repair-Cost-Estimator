"""Append-only audit log (SOC2 seed + carrier sales weapon).

Every estimate, share-token read, PII vault access, and auth event is
logged with a UTC timestamp, actor, event type, and redacted payload.
Log is JSONL on disk (Docker/K8s volume) and optionally streamed to
any OTel-compatible sink via the observability layer.

Rules:
- Never log raw PII (callers pass redacted payloads; defense-in-depth
  re-redacts here).
- Never mutate existing entries. Append-only. Hash-chain each line so
  tampering is detectable (prev_hash -> this_hash).
- Exportable: `export_events()` returns the chain for compliance pulls.
"""

import hashlib
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engines.pii_vault import redact_dict

AUDIT_LOG_PATH = Path(os.environ.get("AUDIT_LOG_PATH", "data/audit_log.jsonl"))
_chain_lock = threading.Lock()
_genesis_hash = "0" * 64


def _current_tail_hash() -> str:
    """Return the hash of the last line in the log (or genesis)."""
    try:
        if not AUDIT_LOG_PATH.exists():
            return _genesis_hash
        last = None
        with AUDIT_LOG_PATH.open("rb") as f:
            for _last in f:
                last = _last
        if not last:
            return _genesis_hash
        rec = json.loads(last.decode("utf-8"))
        return rec.get("this_hash", _genesis_hash)
    except Exception:
        return _genesis_hash


def _hash_event(prev_hash: str, body: dict) -> str:
    canonical = json.dumps({"prev": prev_hash, "body": body}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def log_event(event_type: str, actor: str = "system", payload: dict | None = None, **extra: Any) -> dict:
    """Append one audit event. Returns the stored record (with hashes)."""
    body = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "unix": time.time(),
        "event_type": str(event_type)[:120],
        "actor": str(actor)[:200],
        "payload": redact_dict(payload or {}),
        **{k: v for k, v in extra.items() if k not in ("ts", "unix", "event_type", "actor", "payload")},
    }
    with _chain_lock:
        prev = _current_tail_hash()
        this_hash = _hash_event(prev, body)
        record = {**body, "prev_hash": prev, "this_hash": this_hash}
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return record


def export_events(limit: int = 10_000) -> list[dict]:
    """Return the most recent `limit` audit events (newest last)."""
    if not AUDIT_LOG_PATH.exists():
        return []
    events: list[dict] = []
    with AUDIT_LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events[-limit:]


def verify_chain() -> bool:
    """Recompute the hash chain. Returns False if any entry was tampered."""
    events = export_events(limit=1_000_000)
    prev = _genesis_hash
    for rec in events:
        if rec.get("prev_hash") != prev:
            return False
        body = {k: rec[k] for k in ("ts", "unix", "event_type", "actor", "payload") if k in rec}
        if _hash_event(prev, body) != rec.get("this_hash"):
            return False
        prev = rec["this_hash"]
    return True
