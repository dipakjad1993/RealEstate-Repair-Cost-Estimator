# Security Policy

## Reporting

Report security issues via GitHub Issues or the private contact in the repository profile. Do not open public issues for exploitable vulnerabilities.

## Enterprise hardening (v3.4+)

### Secrets
- `SHARE_SECRET` is **required** for share links. Boot fails if unset or left at the retired dev default `dev-share-secret-change-me`. Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `SHARE_SECRET_PREVIOUS` supports zero-downtime rotation (old tokens verify against the previous key).
- `API_KEY` protects `/v1/estimate_repair`. Auth is timing-safe (`hmac.compare_digest`). For local dev only, `API_AUTH_DISABLED=1` disables auth — never set in production.
- Rotate `SHARE_SECRET` and `API_KEY` on a schedule (90 days recommended) and on personnel changes.

### Transport & headers
- Terminate TLS at the load balancer or reverse proxy. `FORCE_HSTS=1` emits HSTS even behind TLS-terminating proxies.
- Every API response carries: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, and `X-Request-ID`.

### Rate limiting
- In-process sliding window by default. Set `REDIS_URL` for a distributed budget across replicas (falls back to in-memory if Redis is unreachable).

### Audit log
- Append-only JSONL with a SHA-256 hash chain (`data/audit_log.jsonl`, override with `AUDIT_LOG_PATH`).
- Logged events: every estimate, every share-token read, every PII vault access, failed auth attempts.
- Verify integrity: `from engines.audit_log import verify_chain; verify_chain()`.
- PII is redacted before write (defense-in-depth on top of caller redaction).

### PII
- Address/APN/phone/email are redacted in logs and vaulted with TTL only. Never logged raw.

### Dependency supply chain
- Dependabot weekly updates (`.github/dependabot.yml`).
- CI runs `pip-audit` and Trivy filesystem scans on every PR.
- OpenAPI spec is generated from FastAPI in CI and diffed against `static/openapi.json` — drift fails the build.

### Compliance
- `engines/compliance_engine.py` emits the EU AI Act documentation pack (intended purpose, human oversight, training-data provenance: deterministic / none, post-market monitoring).
- ECOA/fair-lending screen: `ecoa_audit()` runs a disparate-impact tercile comparison on ZIP cost modifiers against supplied Census ACS minority-share data.
- All legal templates carry a non-removable `ATTORNEY_REVIEW_REQUIRED: true` flag.

### TLS in Docker/K8s
- The bundled `docker-compose.yml` is for local dev only (HTTP). Production: terminate TLS at ingress (e.g. cert-manager + Let's Encrypt, or your cloud LB), mount `SHARE_SECRET`/`API_KEY` from a secrets manager, and run ≥2 replicas behind the LB with `REDIS_URL` set.
