# Codebase Structure

## Core Sections (Required)

### 1) Top-Level Map

| Path | Purpose | Evidence |
|------|---------|----------|
| `app.py` | Flask application: all routes, API endpoints, startup logic | `app.py` |
| `database.py` | SQLAlchemy models: `ShoppingItem`, `Settings`, `InteractSession` | `database.py` |
| `static/` | Vanilla JS and CSS served directly by Flask | `static/` |
| `templates/` | Jinja2 HTML templates | `templates/` |
| `tests/` | pytest test suite | `tests/` |
| `instance/` | Runtime SQLite database (`shopping_list.db`) — not committed | `instance/shopping_list.db` |
| `requirements.txt` | Python dependency manifest | `requirements.txt` |
| `README.md` | Project overview and deployment guide | `README.md` |

### 2) Entry Points

- Main runtime entry: `app.py` — the Flask `app` object; gunicorn targets `app:app`
- Secondary entry points: None
- How entry is selected: gunicorn `ExecStart` in systemd service (see `README.md`)

### 3) Module Boundaries

| Boundary | What belongs here | What must not be here |
|----------|-------------------|------------------------|
| `app.py` | HTTP routing, request validation, response serialisation, auth middleware, startup migration | Business domain logic (currently mixed in), model definitions |
| `database.py` | SQLAlchemy model classes and `db` instance | Route logic, HTTP concerns |
| `static/` | Client-side JS and CSS | Server-side logic |
| `templates/` | HTML structure and Jinja2 layout | Business logic |
| `tests/` | All test code and fixtures | Production code |

### 4) Naming and Organization Rules

- File naming pattern: `snake_case` for Python files (`app.py`, `database.py`), `snake_case` for static assets (`script.js`, `settings.js`, `style.css`)
- Directory organization pattern: Layer-based (routes, models, templates, static, tests each in their own location)
- Import aliasing or path conventions: No aliasing; `database` imported directly into `app.py` (`from database import db, ShoppingItem, Settings, InteractSession`)

### 5) Evidence

- `docs/codebase/.codebase-scan.txt` (directory tree)
- `app.py`
- `database.py`
