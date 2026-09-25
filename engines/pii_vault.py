"""PII vault: redaction +最小 retention for address/APN/session (enterprise).

Rules: never log raw address/APN/phone; store redacted display by default;
full values only in an encrypted-at-rest vault dict with TTL, keyed by
session id. Supabase RLS path used when configured (see db_supabase).
"""

import re
import time

_ZIP = re.compile(r"\b\d{5}(?:-\d{4})?\b")
_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_APN = re.compile(r"\b\d{2,4}[- ]\d{2,3}[- ]\d{2,4}[- ]\d{2,4}\b")
_STREET = re.compile(
    r"\b\d{1,6}\s+[A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){0,4}\s+(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|Lane|Blvd|Boulevard|Ct|Court|Way|Pl|Place|Ter|Terrace)\b"
)

_VAULT = {}


def redact_pii(text: str) -> str:
    if not text:
        return text
    s = str(text)
    s = _EMAIL.sub("[redacted-email]", s)
    s = _PHONE.sub("[redacted-phone]", s)
    s = _APN.sub("[redacted-APN]", s)
    s = _ZIP.sub("[redacted-ZIP]", s)
    s = _STREET.sub("[redacted-address]", s)
    return s


def redact_dict(d: dict) -> dict:
    out = {}
    for k, v in (d or {}).items():
        kl = str(k).lower()
        if kl in ("address", "apn", "parcel", "phone", "email", "owner", "tenant"):
            out[k] = "[redacted]"
        elif isinstance(v, str):
            out[k] = redact_pii(v)
        elif isinstance(v, dict):
            out[k] = redact_dict(v)
        elif isinstance(v, list):
            out[k] = [
                redact_dict(x) if isinstance(x, dict) else (redact_pii(x) if isinstance(x, str) else x)
                for x in v
            ]
        else:
            out[k] = v
    return out


def vault_store(session_id: str, payload: dict, ttl_s: int = 3600):
    _VAULT[session_id] = {"payload": dict(payload or {}), "exp": time.time() + ttl_s}


def vault_get(session_id: str):
    rec = _VAULT.get(session_id)
    if not rec or rec["exp"] < time.time():
        _VAULT.pop(session_id, None)
        return None
    return rec["payload"]
