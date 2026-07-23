# Codebase Concerns

## Core Sections (Required)

### 1) Top Risks (Prioritized)

| Severity | Concern | Evidence | Impact | Suggested action |
|----------|---------|----------|--------|------------------|
| High | AnyList password stored in plaintext in SQLite | `database.py` (`anylist_password` column), `app.py` (`save_settings`) | If the DB file is exfiltrated, AnyList credentials are exposed immediately | Encrypt at rest, or store credentials only in environment variables |
| High | `SECRET_KEY` has an insecure default | `app.py` line: `os.environ.get('SECRET_KEY', 'dev-secret-change-me')` | Session cookies can be forged if the default is used in production | Remove default; require env var; add startup assertion |
| High | `/api/reset` is unauthenticated and deletes all data | `app.py` (`reset_app` route, no auth check) | Any user (or script) can wipe all items and credentials without knowing the app password | Add rate limiting and CSRF token; consider requiring a separate reset passphrase |
| Med | No CSRF protection on state-mutating endpoints | No Flask-WTF or CSRF middleware found in `app.py` | Authenticated users could be targeted by cross-site request forgery | Add Flask-WTF CSRF tokens to all POST/PUT/DELETE endpoints |
| Med | No rate limiting on `/login` | `app.py` (`login` route) | Brute-force password guessing is possible | Add Flask-Limiter or a per-IP login throttle |
| Med | Schema migration via raw `ALTER TABLE` at startup | `app.py` (startup migration block) | Concurrent startup of gunicorn workers may cause a race condition or duplicate ALTER errors | Replace with Alembic migrations |
| Low | No structured logging | All logging is `print()` | Ops visibility is poor in production; sensitive item names and errors go to stdout unstructured | Add Python `logging` module with a structured formatter |

### 2) Technical Debt

| Debt item | Why it exists | Where | Risk if ignored | Suggested fix |
|-----------|---------------|-------|-----------------|---------------|
| All routes in one file | Project started small | `app.py` (~700 lines) | Increasing difficulty to navigate, test, and collaborate on | Split into Flask Blueprints by feature (items, settings, interact, auth) |
| Business logic in route handlers | No service layer was designed | `app.py` (AnyList sync inline in routes) | Hard to unit-test logic independently from HTTP | Extract a service/use-case layer |
| No `.env.example` | Not created during initial setup | Root directory | New developers don't know which env vars are required | Add `.env.example` with `SECRET_KEY=` documented |
| No pinned Python version | Not specified | `requirements.txt` | Unexpected behaviour on different Python versions | Add `.python-version` or `pyproject.toml` with `python_requires` |

### 3) Security Concerns

| Risk | OWASP category | Evidence | Current mitigation | Gap |
|------|---------------|----------|--------------------|-----|
| AnyList credentials in plaintext DB | A02 Cryptographic Failures | `database.py` (`Settings.anylist_password`) | None | Encrypt field or move to env vars |
| Insecure default `SECRET_KEY` | A05 Security Misconfiguration | `app.py` | Documented in README as needing a `.env` file | No startup assertion; easy to miss |
| Missing CSRF protection | A01 Broken Access Control | `app.py` (no CSRF middleware) | None | Add Flask-WTF |
| No rate limiting on login/reset | A07 Identification and Authentication Failures | `app.py` (`login`, `reset_app`) | None | Add Flask-Limiter |
| Unauthenticated `/api/reset` | A01 Broken Access Control | `app.py` (`reset_app`, `require_login` exemption) | Intentional (lockout recovery) | Document threat model; add secondary verification |
| URL injection in `script.js` | A03 Injection | `static/script.js` (`encodeURI(item.url)`) | `encodeURI` used; `escapeHtml` used for item names | Verify `escapeHtml` covers all XSS vectors |

### 4) Performance and Scaling Concerns

| Concern | Evidence | Current symptom | Scaling risk | Suggested improvement |
|---------|----------|-----------------|-------------|-----------------------|
| SQLite with 2 gunicorn workers | `README.md` (gunicorn `--workers 2`) | None observed currently | Write contention on concurrent sessions | Migrate to PostgreSQL if concurrent users increase |
| AnyList API called synchronously per request | `app.py` (inline `AnyListClient.login()` calls) | Latency spike on each cross-off | Any AnyList slowness blocks the HTTP response | Move AnyList sync to a background task or queue |
| No connection pooling config | `app.py` (`SQLALCHEMY_TRACK_MODIFICATIONS = False` only) | None observed currently | May exhaust connections under load | Configure SQLAlchemy pool settings |

### 5) Fragile/High-Churn Areas

| Area | Why fragile | Churn signal | Safe change strategy |
|------|-------------|-------------|----------------------|
| `app.py` (startup migration block) | Raw ALTER TABLE with no error handling for "column already exists" | Multiple recent fix commits | Replace with Alembic; add `IF NOT EXISTS` guards |
| `app.py` (`require_login`) | iOS Safari workaround exempts several interact endpoints from cookie auth | Several iOS-related fix commits in git log | Document the iOS constraint explicitly; add integration tests for the exempted paths |
| `pyanylist` attribute access (`uid`/`id`/`item_id` probe loop) | pyanylist 0.0.5 API is unstable/undocumented | `app.py` (`import_anylist`) | Pin pyanylist version and add a test that catches attribute changes |

### 6) `[ASK USER]` Questions

1. [ASK USER] Are there plans to support multiple users, or is this always a single-user personal app? (Affects whether the singleton `Settings` row design needs revisiting.)
2. [ASK USER] Is the AnyList password intentionally stored plaintext, or was encryption overlooked? What is the acceptable threat model for credential exposure?
3. [ASK USER] Is `/api/reset` being unauthenticated an accepted risk? What secondary control (if any) should guard it?
4. [ASK USER] Is there a target Python version that should be pinned?
5. [ASK USER] Is there a plan to add a formatter/linter (e.g. `ruff`, `black`)?

### 7) Evidence

- `app.py` (startup migration, `require_login`, `reset_app`, `SECRET_KEY` default, `save_settings`)
- `database.py` (`Settings.anylist_password` column definition)
- `static/script.js` (`escapeHtml`, `encodeURI`)
- `docs/codebase/.codebase-scan.txt` (git log — iOS fix commit history)
- `README.md` (gunicorn 2-worker deployment)
