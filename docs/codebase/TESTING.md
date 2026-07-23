# Testing Patterns

## Core Sections (Required)

### 1) Test Stack and Commands

- Primary test framework: pytest 8.3.5
- Assertion/mocking tools: `unittest.mock.patch` (stdlib); `werkzeug.security.generate_password_hash` used in fixtures
- Commands:

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_api_items.py

# Run with verbose output
pytest -v

# Run with coverage (requires pytest-cov, not in requirements.txt)
# [TODO] coverage not configured
```

### 2) Test Layout

- Test file placement pattern: All tests in a top-level `tests/` directory
- Naming convention: `test_<area>.py` (e.g. `test_api_items.py`, `test_models.py`, `test_edge_adversarial.py`)
- Setup files: `tests/conftest.py` — defines shared fixtures and stubs out `pyanylist` before any app import

### 3) Test Scope Matrix

| Scope | Covered? | Typical target | Notes |
|-------|----------|----------------|-------|
| Unit | Yes | SQLAlchemy models (`test_models.py`) | Model `to_dict()`, property accessors |
| Integration | Yes | Flask REST API endpoints | `test_api_items.py`, `test_api_anylist.py`, `test_api_csv.py`, `test_api_interact.py`, `test_api_settings_auth.py` |
| User stories / E2E | Yes (simulated) | Full user workflows | `test_user_stories.py` — multi-step flows via test client |
| Adversarial/edge cases | Yes | Boundary inputs, auth bypass attempts | `test_edge_adversarial.py` |
| Browser/real E2E | No | Actual browser + Berkeley Bowl site | Not applicable — requires live browser |

### 4) Mocking and Isolation Strategy

- **pyanylist stub**: Injected into `sys.modules` in `conftest.py` before any import of `app`. Provides a `_StubAnyListClient` that returns empty lists and no-ops. All AnyList-specific tests layer `unittest.mock.patch` on top of this stub.
- **Database isolation**: Each test uses an in-memory SQLite DB (`sqlite:///:memory:`) created fresh per test via the `app` fixture; dropped after each test.
- **Authentication fixtures**: Three client variants — `client` (unauthenticated), `auth_client` (pre-authenticated via session), `no_password_client` (app has no password set).
- Common failure mode: Tests that forget to use `app_context()` when querying the DB directly will fail with "Working outside of application context".

### 5) Coverage and Quality Signals

- Coverage tool + threshold: [TODO] — `pytest-cov` not in `requirements.txt`; no `.coveragerc`
- Current reported coverage: [TODO]
- Known gaps:
  - No tests for the Jinja2 template rendering beyond status codes
  - No tests for the `/api/reset` unauthenticated endpoint's security implications (intentional open access)
  - No tests for the `interact_heartbeat` timeout/expiry path

### 6) Evidence

- `tests/conftest.py` (fixtures, pyanylist stub)
- `tests/test_api_items.py` (representative API tests)
- `tests/test_edge_adversarial.py` (adversarial coverage)
- `tests/test_user_stories.py` (end-to-end flows)
- `requirements.txt` (pytest 8.3.5)
