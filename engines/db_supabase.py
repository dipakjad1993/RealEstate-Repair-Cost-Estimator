"""Supabase/Postgres persistence with sqlite dev fallback (ScopeProof v4.0).

- If SUPABASE_URL + key configured: INSERT into the `estimates` table via the
  supabase client. RLS policies are NOT applied by this module — SCHEMA_SQL
  contains an example policy that the operator must install and verify.
- If DATABASE_URL is set: backend() reports "postgres", but no insert path is
  wired for it yet; save_estimate returns an error status. Never claim a write.
- Else: local sqlite cache at data/repair_estimator.db (dev/single-tenant).
- Only redacted zip5/state/totals/findings are written; no raw address/APN
  columns exist in either schema.
"""

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))

SCHEMA_SQL = """
create table if not exists estimates (
  id uuid default gen_random_uuid() primary key,
  tenant_id text not null,
  address_redacted text,
  zip5 text,
  state text,
  totals jsonb,
  findings jsonb,
  provenance jsonb,
  created_at timestamptz default now()
);
alter table estimates enable row level security;
-- Example RLS (run once as owner):
-- create policy tenant_isolation on estimates for all using (tenant_id = current_setting('app.tenant_id', true));
"""


def backend() -> str:
    if SUPABASE_URL and SUPABASE_KEY:
        return "supabase"
    if os.environ.get("DATABASE_URL"):
        return "postgres"
    return "sqlite"


def save_estimate(tenant_id: str, estimate: dict) -> dict:
    """Persist minimal estimate row. Returns {backend, id|rowid}."""
    rec = {
        "tenant_id": tenant_id or "public",
        "zip5": str((estimate.get("zip") or "")[:5]),
        "state": estimate.get("state", ""),
        "totals": estimate.get("totals", {}),
        "findings": estimate.get("findings", [])[:500],
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    b = backend()
    if b == "sqlite":
        import sqlite3

        from config import DB_PATH

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""CREATE TABLE IF NOT EXISTS estimates
          (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT, zip5 TEXT, state TEXT,
           totals TEXT, created_at TEXT)""")
        cur = conn.execute(
            "INSERT INTO estimates (tenant,zip5,state,totals,created_at) VALUES (?,?,?,?,?)",
            (rec["tenant_id"], rec["zip5"], rec["state"], json.dumps(rec["totals"]), rec["created_at"]),
        )
        conn.commit()
        rowid = cur.lastrowid
        conn.close()
        return {"backend": "sqlite", "id": rowid}
    try:
        from supabase import create_client

        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = (
            sb.table("estimates")
            .insert(
                {
                    "tenant_id": rec["tenant_id"],
                    "zip5": rec["zip5"],
                    "state": rec["state"],
                    "totals": rec["totals"],
                    "findings": rec["findings"],
                }
            )
            .execute()
        )
        return {"backend": "supabase", "id": str((res.data or [{}])[0].get("id", ""))}
    except Exception as e:
        logger.warning(f"supabase save failed (no write performed): {e}")
        return {"backend": "unavailable", "error": str(e)[:200]}
