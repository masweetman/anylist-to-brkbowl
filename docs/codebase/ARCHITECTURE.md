# Architecture

## Core Sections (Required)

### 1) Architectural Style

- Primary style: Monolithic MVC-style layered web application
- Why this classification: A single `app.py` hosts all routes (controller), `database.py` contains all models, and `templates/` holds all views. No service layer or domain packages.
- Primary constraints:
  1. Single-file route concentration — all ~25 endpoints live in `app.py`
  2. SQLite single-file database — limits concurrent writes and horizontal scaling
  3. Stateless pages + DB-backed sessions — `InteractSession` is persisted in the DB so multiple gunicorn workers can share state

### 2) System Flow

```text
Browser / iOS client
  -> Flask route (app.py: require_login middleware)
  -> Route handler (validates input, calls db.session / pyanylist)
  -> SQLAlchemy ORM (database.py: ShoppingItem / Settings / InteractSession)
  -> SQLite (instance/shopping_list.db)
  -> JSON response or Jinja2 rendered HTML
  -> Client-side JS (static/script.js or static/settings.js) updates DOM
```

**Interactive cart flow (two-tab):**
```text
Main tab: POST /api/add-to-cart
  -> Creates InteractSession in DB (UUID session_id)
  -> Returns interact_url

New tab: GET /interact?session_id=<uuid>
  -> Polls GET /api/interact/status/<session_id>
  -> Navigates to product URL or Berkeley Bowl search
  -> User clicks "Added to cart" → POST /api/interact/item-complete/<session_id>
  -> AnyList cross-off attempted via pyanylist
  -> Advances index; continues until all items processed
```

### 3) Layer/Module Responsibilities

| Layer or module | Owns | Must not own | Evidence |
|-----------------|------|--------------|----------|
| `app.py` (routes) | HTTP parsing, auth guard, response formatting, session management | Model definitions, raw SQL | `app.py` |
| `database.py` (models) | ORM schema, `to_dict()` serialisation, `items` property (JSON de/serialisation) | Route logic | `database.py` |
| `static/script.js` | Main list UI logic, AnyList import modal, CSV import/export | Server-side state | `static/script.js` |
| `static/settings.js` | Settings form, password management UI | Shopping list logic | `static/settings.js` |
| `templates/` | Page skeletons, Jinja2 variable injection | Client-state management | `templates/` |

### 4) Reused Patterns

| Pattern | Where found | Why it exists |
|---------|-------------|---------------|
| Before-request auth guard | `app.py` (`require_login()`) | Centralises session cookie check across all protected routes |
| Singleton settings row | `app.py` (`Settings.query.first()`) | App has exactly one user; settings are a single DB row |
| DB-backed session state | `database.py` (`InteractSession`) | Gunicorn workers are separate processes; in-memory state would be lost between requests |
| Lazy `pyanylist` import | `app.py` (inside route handlers) | Allows the app to start even if pyanylist is missing or its Rust extension fails to load |

### 5) Known Architectural Risks

- **All routes in one file**: `app.py` is already ~700 lines. Growth will make it increasingly hard to navigate and test in isolation.
- **SQLite in production**: Concurrent write contention is a risk if multiple users or workers hit write-heavy endpoints simultaneously. The gunicorn config uses 2 workers.
- **No service layer**: Business logic (AnyList sync, item deduplication, session management) is embedded directly in route handlers, making it tightly coupled to HTTP concerns and harder to unit-test.

### 6) Evidence

- `app.py` (all routes and middleware)
- `database.py` (all models)
- `README.md` (gunicorn 2-worker deployment)
- `tests/conftest.py` (in-memory SQLite for testing confirms DB is the sole state store)
