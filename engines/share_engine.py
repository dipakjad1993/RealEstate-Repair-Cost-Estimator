"""Lender-ready share links + branded PDF portal (enterprise).

Public URL (not just download): an estimate snapshot is sealed with an HMAC
token and servable at /s/{token} via the FastAPI backend or Streamlit
query-param (?share=token). Snapshot contains redacted PII + totals +
line items + provenance + expiry.
"""

import base64
import hashlib
import hmac
import json
import os
import time

SECRET = os.environ.get("SHARE_SECRET", "dev-share-secret-change-me")
TTL_S = 30 * 24 * 3600


def seal_snapshot(snapshot: dict, ttl_s: int = TTL_S) -> str:
    body = {"snapshot": snapshot, "exp": int(time.time()) + ttl_s}
    raw = json.dumps(body, sort_keys=True).encode()
    sig = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(raw).decode().rstrip("=") + "." + sig
    return token


def open_snapshot(token: str):
    try:
        raw_b64, sig = token.rsplit(".", 1)
        raw = base64.urlsafe_b64decode(raw_b64 + "=" * (-len(raw_b64) % 4))
        if hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest() != sig:
            return None
        body = json.loads(raw.decode())
        if body.get("exp", 0) < time.time():
            return None
        return body.get("snapshot")
    except Exception:
        return None


def share_url(token: str, base_url: str = "") -> str:
    base = (base_url or os.environ.get("APP_BASE_URL", "http://localhost:8501")).rstrip("/")
    return f"{base}/?share={token}"
