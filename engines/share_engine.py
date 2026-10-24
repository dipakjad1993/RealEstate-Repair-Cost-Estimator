"""Lender-ready share links + branded PDF portal (enterprise).

Public URL (not just download): an estimate snapshot is sealed with an HMAC
token and servable at /s/{token} via the FastAPI backend or Streamlit
query-param (?share=token). Snapshot contains redacted PII + totals +
line items + provenance + expiry.

Security (v3.4+):
- SHARE_SECRET must be set explicitly. Boot fails if missing or left at
  the retired dev default. Rotation supported via SHARE_SECRET_PREVIOUS.
- Signature verification uses hmac.compare_digest (timing-safe).
- Tokens carry a key-id suffix so rotation can invalidate old tokens.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

_DEV_DEFAULT_SECRET = "dev-share-secret-change-me"
TTL_S = 30 * 24 * 3600


class ShareSecretError(RuntimeError):
    """Raised at import/boot when SHARE_SECRET is missing or insecure."""


def _current_secret() -> str:
    return os.environ.get("SHARE_SECRET", "").strip()


def _previous_secret() -> str:
    return os.environ.get("SHARE_SECRET_PREVIOUS", "").strip()


def _require_secure_secret() -> str:
    secret = _current_secret()
    if not secret:
        raise ShareSecretError(
            "SHARE_SECRET env var is required. Generate one with: "
            'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    if secret == _DEV_DEFAULT_SECRET:
        raise ShareSecretError(
            "SHARE_SECRET is still the retired dev default. "
            'Rotate it before deploying: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    if len(secret) < 32:
        raise ShareSecretError("SHARE_SECRET must be at least 32 characters for HMAC-SHA256.")
    return secret


def get_secret() -> str:
    """Lazily validated secret accessor. Import-time check happens at boot."""
    return _require_secure_secret()


def _sign(raw: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def _key_id() -> str:
    """Short id of the active key so tokens can be attributed to a generation."""
    return hashlib.sha256(_current_secret().encode("utf-8")).hexdigest()[:8]


def seal_snapshot(snapshot: dict[str, Any], ttl_s: int = TTL_S) -> str:
    secret = _require_secure_secret()
    body = {"snapshot": snapshot, "exp": int(time.time()) + ttl_s, "kid": _key_id()}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = _sign(raw, secret)
    return base64.urlsafe_b64encode(raw).decode().rstrip("=") + "." + sig


def open_snapshot(token: str) -> dict[str, Any] | None:
    """Verify + decode. Tries current secret first, then previous (rotation)."""
    current = _current_secret()
    previous = _previous_secret()
    secrets_to_try = [current] if current else []
    if previous:
        secrets_to_try.append(previous)
    if not secrets_to_try:
        # Unconfigured dev: refuse to validate anything (fail closed).
        return None
    try:
        raw_b64, sig = token.rsplit(".", 1)
        raw = base64.urlsafe_b64decode(raw_b64 + "=" * (-len(raw_b64) % 4))
    except Exception:
        return None
    for candidate in secrets_to_try:
        if hmac.compare_digest(_sign(raw, candidate), sig):
            try:
                body = json.loads(raw.decode("utf-8"))
            except Exception:
                return None
            if body.get("exp", 0) < time.time():
                return None
            return body.get("snapshot")
    return None


def share_url(token: str, base_url: str = "") -> str:
    base = (base_url or os.environ.get("APP_BASE_URL", "http://localhost:8501")).rstrip("/")
    return f"{base}/s/{token}"


def validate_share_secret() -> str:
    """Boot-time guard. Call from API/server startup to fail fast on insecure config."""
    return _require_secure_secret()
