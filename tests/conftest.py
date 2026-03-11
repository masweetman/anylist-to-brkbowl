"""
Shared pytest fixtures for the anylist-to-brkbowl test suite.
"""
import sys
import types
import pytest
from werkzeug.security import generate_password_hash

# ---------------------------------------------------------------------------
# Stub out pyanylist before any app code is imported, because pyanylist is a
# Rust-backed package that cannot be installed in this environment.  All tests
# that exercise AnyList integration use mocks on top of this stub.
# ---------------------------------------------------------------------------
_pyanylist_stub = types.ModuleType("pyanylist")

class _StubAnyListClient:
    """Minimal stub so that `from pyanylist import AnyListClient` works."""
    @classmethod
    def login(cls, email, password):
        return cls()

    def get_lists(self):
        return []

    def get_list_by_name(self, name):
        return None

    def cross_off_item(self, list_id, item_id):
        pass

    def uncheck_item(self, list_id, item_id):
        pass

_pyanylist_stub.AnyListClient = _StubAnyListClient
sys.modules["pyanylist"] = _pyanylist_stub

# Now it is safe to import the app
from app import app as flask_app  # noqa: E402
from database import db, ShoppingItem, Settings, InteractSession  # noqa: E402


# ---------------------------------------------------------------------------
# App / DB fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def app():
    """Create a fresh Flask application configured for testing."""
    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SECRET_KEY="test-secret",
        WTF_CSRF_ENABLED=False,
    )

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Flask test client (unauthenticated by default)."""
    return app.test_client()


@pytest.fixture()
def auth_client(app):
    """Flask test client pre-authenticated via session cookie."""
    with app.app_context():
        settings = Settings()
        settings.app_password = generate_password_hash("testpass")
        db.session.add(settings)
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["authenticated"] = True
    return client


@pytest.fixture()
def no_password_client(app):
    """Flask test client when no app password is configured (open access)."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_item(app):
    """A single ShoppingItem persisted in the test DB."""
    with app.app_context():
        item = ShoppingItem(name="Apples", url="https://example.com/apples", complete=False)
        db.session.add(item)
        db.session.commit()
        # Detach so callers can read attributes outside the session
        db.session.expunge(item)
        return item


@pytest.fixture()
def sample_items(app):
    """Several ShoppingItems covering complete/incomplete and url/no-url states."""
    with app.app_context():
        items = [
            ShoppingItem(name="Apples",  url="https://example.com/apples",  complete=False),
            ShoppingItem(name="Bananas", url="",                             complete=False),
            ShoppingItem(name="Carrots", url="https://example.com/carrots", complete=True),
            ShoppingItem(name="Dates",   url="",                             complete=True),
        ]
        for i in items:
            db.session.add(i)
        db.session.commit()
        for i in items:
            db.session.expunge(i)
        return items


@pytest.fixture()
def anylist_session(app, sample_items):
    """
    A pre-created interactive session in the database, seeded with the
    incomplete items from sample_items.
    """
    import uuid, time
    with app.app_context():
        incomplete = ShoppingItem.query.filter_by(complete=False).all()
        item_list = [
            {
                "id": i.id,
                "name": i.name,
                "url": i.url,
                "anylist_item_id": i.anylist_item_id,
                "anylist_list_id": i.anylist_list_id,
                "complete": False,
            }
            for i in incomplete
        ]

        session_id = str(uuid.uuid4())
        sess = InteractSession(
            id=session_id,
            items=item_list,
            current_index=0,
            state='running',
            last_heartbeat=time.time(),
        )
        db.session.add(sess)
        db.session.commit()

    yield session_id

    with app.app_context():
        InteractSession.query.filter_by(id=session_id).delete()
        db.session.commit()
