# Coding Conventions

## Core Sections (Required)

### 1) Naming Rules

| Item | Rule | Example | Evidence |
|------|------|---------|----------|
| Python files | `snake_case` | `app.py`, `database.py` | `docs/codebase/.codebase-scan.txt` |
| Route/view functions | `snake_case` verb–noun | `get_items`, `add_item`, `import_anylist` | `app.py` |
| Model classes | `PascalCase` | `ShoppingItem`, `InteractSession` | `database.py` |
| DB table names | `snake_case` plural | `shopping_items`, `interact_sessions` | `database.py` (`__tablename__`) |
| JS files | `snake_case` | `script.js`, `settings.js` | `static/` |
| JS functions | `camelCase` | `loadItems`, `renderItems`, `toggleComplete` | `static/script.js` |
| HTML templates | `snake_case` | `index.html`, `interact.html` | `templates/` |

### 2) Formatting and Linting

- Formatter: None configured (no `pyproject.toml`, `.flake8`, `.pylintrc`, or `.prettierrc` found)
- Linter: None configured
- Enforced rules: None automated — [ASK USER] whether a formatter/linter is planned
- Run commands: N/A

### 3) Import and Module Conventions

- Import grouping/order: stdlib → third-party → local (`app.py` follows this loosely: `csv`, `json`, `os`, `time` first; then Flask/Werkzeug; then `database`)
- Alias vs relative import policy: No aliases; absolute local imports (`from database import db, ...`)
- Public exports/barrel policy: None; `database.py` exposes everything at module level

### 4) Error and Logging Conventions

- Error strategy by layer: Route handlers wrap logic in `try/except Exception` and return `jsonify({'error': str(e)}), 5xx`. AnyList sync errors are caught and printed but do **not** fail the request (best-effort sync).
- Logging style: `print()` statements only — no structured logging library. Example: `print(f"✅ Crossed off in AnyList: {db_item.name}")`
- Sensitive-data redaction: Not implemented — AnyList credentials and item names may appear in stdout logs.

### 5) Testing Conventions

- Test file naming/location rule: All tests in `tests/` directory; files named `test_<area>.py`
- Mocking strategy: `unittest.mock.patch` for pyanylist and external calls; pyanylist is also stubbed at the module level in `conftest.py` before any app code imports
- Coverage expectation: [TODO] — no coverage configuration found

### 6) Evidence

- `app.py` (import order, error handling patterns)
- `database.py` (model naming)
- `static/script.js` (JS naming)
- `tests/conftest.py` (test conventions)
