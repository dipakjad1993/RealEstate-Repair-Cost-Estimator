"""Ensure repo root is importable in CI regardless of pytest invocation.

Also isolates the append-only audit log: any test that does not monkeypatch
AUDIT_LOG_PATH must NOT write into the real data/audit_log.jsonl. The suite
runs with the log pointed at a temp file for the whole session.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Must be set before engines.audit_log is imported anywhere in the session.
os.environ.setdefault(
    "AUDIT_LOG_PATH",
    str(Path(tempfile.gettempdir()) / "scopeproof_pytest_audit_log.jsonl"),
)
