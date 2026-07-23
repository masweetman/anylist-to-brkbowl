# External Integrations

## Core Sections (Required)

### 1) Integration Inventory

| System | Type | Purpose | Auth model | Criticality | Evidence |
|--------|------|---------|------------|-------------|----------|
| AnyList | Third-party API (via pyanylist) | Import shopping list items; bidirectional check-off sync | Email + password stored in `Settings` DB row | Medium (gracefully degrades — sync failures are non-fatal) | `app.py` (`import_anylist`, `update_item`, `interact_item_complete`) |
| Berkeley Bowl website | External website (user-navigated) | User manually adds items to their cart; app provides product URLs or search prompts | None (user's own browser session) | Medium (core UX flow) | `app.py` (`interact_status`) |
| SQLite | Embedded relational DB | Primary data store for all app state | Filesystem access only | High | `database.py`, `app.py` config |

### 2) Data Stores

| Store | Role | Access layer | Key risk | Evidence |
|-------|------|--------------|----------|----------|
| SQLite (`instance/shopping_list.db`) | Single source of truth for items, settings, and interact sessions | Flask-SQLAlchemy ORM (`database.py`) | Write contention with multiple gunicorn workers; data loss if file is deleted | `app.py` (`SQLALCHEMY_DATABASE_URI`) |

### 3) Secrets and Credentials Handling

- Credential sources:
  - **AnyList email/password**: stored in plaintext in the `Settings` SQLite table (`anylist_email`, `anylist_password` columns). No encryption at rest.
  - **App password**: stored as a Werkzeug `pbkdf2:sha256` hash in `Settings.app_password`.
  - **Flask `SECRET_KEY`**: read from env var; falls back to a hardcoded default `'dev-secret-change-me'`.
- Hardcoding checks: `SECRET_KEY` has an insecure hardcoded default — **must be overridden in production**.
- Rotation or lifecycle notes: No credential rotation mechanism exists. Changing the AnyList password requires updating the Settings page manually.

### 4) Reliability and Failure Behavior

- Retry/backoff behavior: None — AnyList API calls are fire-and-forget; failures are caught, printed, and ignored.
- Timeout policy: Not configured — pyanylist calls have no explicit timeout.
- Circuit-breaker or fallback behavior: None. The app continues normally if AnyList sync fails.

### 5) Observability for Integrations

- Logging around external calls: `print()` statements log AnyList success/failure inline (e.g. `"✅ Crossed off in AnyList"`, `"⚠️ Could not cross off in AnyList"`).
- Metrics/tracing coverage: None.
- Missing visibility gaps: No structured logging, no request tracing, no alerting on AnyList errors.

### 6) Evidence

- `app.py` (`import_anylist`, `update_item`, `interact_item_complete` route handlers)
- `database.py` (`Settings` model — `anylist_email`, `anylist_password` columns)
- `app.py` (line: `app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')`)
