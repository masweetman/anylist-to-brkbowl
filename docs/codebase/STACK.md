# Technology Stack

## Core Sections (Required)

### 1) Runtime Summary

| Area | Value | Evidence |
|------|-------|----------|
| Primary language | Python 3 | `requirements.txt`, `app.py` |
| Runtime + version | CPython 3 (no pinned version) | `requirements.txt` (no `python_requires`) |
| Package manager | pip | `requirements.txt` |
| Module/build system | None — direct Python execution / gunicorn | `README.md` (deployment section) |

### 2) Production Frameworks and Dependencies

| Dependency | Version | Role in system | Evidence |
|------------|---------|----------------|----------|
| Flask | 2.3.3 | Web framework, routing, templating | `requirements.txt`, `app.py` |
| Flask-SQLAlchemy | 3.0.5 | ORM and database session management | `requirements.txt`, `database.py` |
| Werkzeug | 2.3.7 | Password hashing, WSGI utilities | `requirements.txt`, `app.py` |
| pyanylist | 0.0.5 | AnyList API client (Rust-backed) | `requirements.txt`, `app.py` |
| python-dotenv | 1.0.0 | `.env` file loading at startup | `requirements.txt`, `app.py` |

### 3) Development Toolchain

| Tool | Purpose | Evidence |
|------|---------|----------|
| pytest | Test runner | `requirements.txt` |
| gunicorn | Production WSGI server | `README.md` (systemd service) |
| nginx | Reverse proxy in production | `README.md` (Nginx config section) |

### 4) Key Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
flask run   # or: python app.py

# Run tests
pytest

# Run production server (as configured in README)
gunicorn --workers 2 --bind 127.0.0.1:5001 app:app
```

### 5) Environment and Config

- Config sources: `.env` file (loaded via `python-dotenv`), environment variables
- Required env vars:
  - `SECRET_KEY` — Flask session secret; has an insecure default `'dev-secret-change-me'` — **must be set in production**
  - `FLASK_ENV` — mentioned in README deployment guide (`production`)
- Deployment/runtime constraints: Designed for Ubuntu + nginx + gunicorn; SQLite database stored at `instance/shopping_list.db`

### 6) Evidence

- `requirements.txt`
- `app.py` (lines 1–20: imports and config)
- `README.md` (deployment section)
