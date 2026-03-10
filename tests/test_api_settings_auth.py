"""
Integration tests for:
  - Settings API:  GET/POST /api/settings, POST /api/settings/password
  - Auth routes:   GET/POST /login, GET /logout
  - require_login middleware
"""
import json
import pytest
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, Settings, ShoppingItem


# ---------------------------------------------------------------------------
# Settings API
# ---------------------------------------------------------------------------

class TestGetSettings:
    """GET /api/settings"""

    def test_returns_200(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 200

    def test_creates_default_settings_if_none_exist(self, client, app):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        with app.app_context():
            assert Settings.query.count() == 1

    def test_response_shape(self, client):
        resp = client.get("/api/settings")
        data = resp.get_json()
        assert "id" in data
        assert "anylist_email" in data
        assert "anylist_password" in data
        assert "anylist_list_name" in data
        assert "has_password" in data
        assert "updated_at" in data

    def test_has_password_false_by_default(self, client):
        resp = client.get("/api/settings")
        assert resp.get_json()["has_password"] is False

    def test_has_password_true_when_set(self, app):
        with app.app_context():
            s = Settings(app_password=generate_password_hash("secret"))
            db.session.add(s)
            db.session.commit()
        # Use an authenticated client so require_login doesn't block the request
        auth = app.test_client()
        with auth.session_transaction() as sess:
            sess["authenticated"] = True
        resp = auth.get("/api/settings")
        assert resp.get_json()["has_password"] is True

    def test_app_password_hash_not_in_response(self, app, client):
        with app.app_context():
            s = Settings(app_password=generate_password_hash("secret"))
            db.session.add(s)
            db.session.commit()
        resp = client.get("/api/settings")
        assert "app_password" not in resp.get_json()


class TestSaveSettings:
    """POST /api/settings"""

    def test_save_email(self, client, app):
        resp = client.post(
            "/api/settings",
            data=json.dumps({"anylist_email": "user@example.com"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        with app.app_context():
            assert Settings.query.first().anylist_email == "user@example.com"

    def test_save_password(self, client, app):
        resp = client.post(
            "/api/settings",
            data=json.dumps({"anylist_password": "hunter2"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        with app.app_context():
            assert Settings.query.first().anylist_password == "hunter2"

    def test_save_list_name(self, client, app):
        resp = client.post(
            "/api/settings",
            data=json.dumps({"anylist_list_name": "Groceries"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        with app.app_context():
            assert Settings.query.first().anylist_list_name == "Groceries"

    def test_save_all_fields(self, client, app):
        payload = {
            "anylist_email": "a@b.com",
            "anylist_password": "pass",
            "anylist_list_name": "Weekly",
        }
        resp = client.post(
            "/api/settings",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["anylist_email"] == "a@b.com"
        assert data["anylist_list_name"] == "Weekly"

    def test_save_creates_settings_if_none_exist(self, client, app):
        with app.app_context():
            assert Settings.query.count() == 0
        client.post(
            "/api/settings",
            data=json.dumps({"anylist_email": "new@example.com"}),
            content_type="application/json",
        )
        with app.app_context():
            assert Settings.query.count() == 1

    def test_save_updates_existing_settings(self, client, app):
        with app.app_context():
            db.session.add(Settings(anylist_email="old@example.com"))
            db.session.commit()
        client.post(
            "/api/settings",
            data=json.dumps({"anylist_email": "new@example.com"}),
            content_type="application/json",
        )
        with app.app_context():
            assert Settings.query.count() == 1
            assert Settings.query.first().anylist_email == "new@example.com"

    def test_partial_update_does_not_clear_other_fields(self, client, app):
        with app.app_context():
            db.session.add(Settings(
                anylist_email="keep@example.com",
                anylist_list_name="Keep",
            ))
            db.session.commit()
        client.post(
            "/api/settings",
            data=json.dumps({"anylist_password": "newpass"}),
            content_type="application/json",
        )
        with app.app_context():
            s = Settings.query.first()
            assert s.anylist_email == "keep@example.com"
            assert s.anylist_list_name == "Keep"
            assert s.anylist_password == "newpass"


class TestSetAppPassword:
    """POST /api/settings/password"""

    def test_set_password_returns_200(self, client):
        resp = client.post(
            "/api/settings/password",
            data=json.dumps({"password": "newpass"}),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_set_password_has_password_true(self, client):
        resp = client.post(
            "/api/settings/password",
            data=json.dumps({"password": "newpass"}),
            content_type="application/json",
        )
        assert resp.get_json()["has_password"] is True

    def test_set_password_stored_as_hash(self, client, app):
        client.post(
            "/api/settings/password",
            data=json.dumps({"password": "mypassword"}),
            content_type="application/json",
        )
        with app.app_context():
            s = Settings.query.first()
            assert s.app_password is not None
            assert s.app_password != "mypassword"
            assert check_password_hash(s.app_password, "mypassword")

    def test_clear_password_with_empty_string(self, app):
        # Set a password first
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("toremove")))
            db.session.commit()
        # Use an authenticated client to clear it
        auth = app.test_client()
        with auth.session_transaction() as sess:
            sess["authenticated"] = True
        resp = auth.post(
            "/api/settings/password",
            data=json.dumps({"password": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["has_password"] is False
        with app.app_context():
            assert Settings.query.first().app_password is None

    def test_clear_password_with_whitespace(self, app):
        """Whitespace-only password is treated as empty (cleared)."""
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("existing")))
            db.session.commit()
        auth = app.test_client()
        with auth.session_transaction() as sess:
            sess["authenticated"] = True
        resp = auth.post(
            "/api/settings/password",
            data=json.dumps({"password": "   "}),
            content_type="application/json",
        )
        assert resp.get_json()["has_password"] is False

    def test_set_password_creates_settings_if_none(self, client, app):
        with app.app_context():
            assert Settings.query.count() == 0
        client.post(
            "/api/settings/password",
            data=json.dumps({"password": "init"}),
            content_type="application/json",
        )
        with app.app_context():
            assert Settings.query.count() == 1


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

class TestLoginRoute:
    """GET/POST /login"""

    def test_get_login_returns_200(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_login_page_renders_html(self, client):
        resp = client.get("/login")
        assert b"<html" in resp.data.lower() or b"<!doctype" in resp.data.lower()

    def test_post_correct_password_redirects(self, app, client):
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("correct")))
            db.session.commit()
        resp = client.post("/login", data={"password": "correct"})
        assert resp.status_code == 302
        assert "/" in resp.headers["Location"]

    def test_post_wrong_password_stays_on_login(self, app, client):
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("correct")))
            db.session.commit()
        resp = client.post("/login", data={"password": "wrong"})
        assert resp.status_code == 200
        assert b"Incorrect" in resp.data

    def test_post_correct_password_sets_session(self, app, client):
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("correct")))
            db.session.commit()
        with client.session_transaction() as sess:
            assert not sess.get("authenticated")
        client.post("/login", data={"password": "correct"})
        with client.session_transaction() as sess:
            assert sess.get("authenticated") is True

    def test_login_when_no_password_set_fails(self, app, client):
        """When no password is configured, POST /login always fails with 200+error.
        The code checks `settings and settings.app_password`; with no settings row
        check_password_hash is never called so the error branch is always taken."""
        resp = client.post("/login", data={"password": "anything"})
        assert resp.status_code == 200
        assert b"Incorrect" in resp.data


class TestLogoutRoute:
    """GET /logout"""

    def test_logout_redirects_to_login(self, client):
        resp = client.get("/logout")
        assert resp.status_code == 302
        assert "login" in resp.headers["Location"]

    def test_logout_clears_session(self, app, client):
        with client.session_transaction() as sess:
            sess["authenticated"] = True
        client.get("/logout")
        with client.session_transaction() as sess:
            assert not sess.get("authenticated")


# ---------------------------------------------------------------------------
# require_login middleware
# ---------------------------------------------------------------------------

class TestRequireLogin:
    """Tests for the require_login before_request hook."""

    def test_unauthenticated_api_request_returns_401_when_password_set(self, app):
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("pass")))
            db.session.commit()
        unauth = app.test_client()
        resp = unauth.get("/api/items")
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "Authentication required"

    def test_unauthenticated_page_request_redirects_to_login_when_password_set(self, app):
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("pass")))
            db.session.commit()
        unauth = app.test_client()
        resp = unauth.get("/")
        assert resp.status_code == 302
        assert "login" in resp.headers["Location"]

    def test_authenticated_request_passes_through(self, auth_client):
        resp = auth_client.get("/api/items")
        assert resp.status_code == 200

    def test_login_endpoint_always_accessible(self, app):
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("pass")))
            db.session.commit()
        unauth = app.test_client()
        resp = unauth.get("/login")
        assert resp.status_code == 200

    def test_interact_endpoint_accessible_without_auth(self, app):
        """The /interact page is exempt from auth (iOS Safari workaround)."""
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("pass")))
            db.session.commit()
        unauth = app.test_client()
        resp = unauth.get("/interact")
        assert resp.status_code == 200

    def test_interact_api_endpoints_accessible_without_auth(self, app):
        """interact_status, item_complete, item_skip, heartbeat skip auth."""
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("pass")))
            db.session.commit()
        unauth = app.test_client()
        # These return 404 (session not found) not 401
        for path in [
            "/api/interact/status/fake-id",
            "/api/interact/heartbeat/fake-id",
        ]:
            resp = unauth.get(path) if "status" in path else unauth.post(path)
            assert resp.status_code != 401, f"{path} should not require auth"

    def test_no_password_allows_all_access(self, no_password_client):
        """When no password is set, all endpoints are accessible."""
        resp = no_password_client.get("/api/items")
        assert resp.status_code == 200
        resp = no_password_client.get("/")
        assert resp.status_code == 200

    def test_reset_endpoint_accessible_without_auth(self, app):
        """POST /api/reset must be reachable even when a password is set (lockout recovery)."""
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("locked")))
            db.session.commit()
        unauth = app.test_client()
        resp = unauth.post("/api/reset")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Reset endpoint
# ---------------------------------------------------------------------------

class TestResetApp:
    """POST /api/reset — forgot-password factory reset."""

    def test_reset_returns_200(self, client):
        resp = client.post("/api/reset")
        assert resp.status_code == 200

    def test_reset_returns_success_true(self, client):
        resp = client.post("/api/reset")
        assert resp.get_json()["success"] is True

    def test_reset_deletes_all_shopping_items(self, client, app):
        with app.app_context():
            db.session.add(ShoppingItem(name="Milk"))
            db.session.add(ShoppingItem(name="Eggs"))
            db.session.commit()
        client.post("/api/reset")
        with app.app_context():
            assert ShoppingItem.query.count() == 0

    def test_reset_clears_app_password(self, client, app):
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("secret")))
            db.session.commit()
        client.post("/api/reset")
        with app.app_context():
            s = Settings.query.first()
            assert s is None or s.app_password is None

    def test_reset_clears_anylist_credentials(self, client, app):
        with app.app_context():
            db.session.add(Settings(
                anylist_email="user@example.com",
                anylist_password="anylistpass",
                anylist_list_name="Groceries",
            ))
            db.session.commit()
        client.post("/api/reset")
        with app.app_context():
            s = Settings.query.first()
            if s:
                assert s.anylist_email is None
                assert s.anylist_password is None
                assert s.anylist_list_name is None

    def test_reset_allows_unauthenticated_access_after(self, app):
        """After reset, the app is open (no password) so any client can access it."""
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("locked")))
            db.session.add(ShoppingItem(name="Item1"))
            db.session.commit()
        unauth = app.test_client()
        unauth.post("/api/reset")
        resp = unauth.get("/api/items")
        assert resp.status_code == 200

    def test_reset_with_no_settings_row_still_succeeds(self, client, app):
        """Reset should succeed even if there is no Settings row."""
        with app.app_context():
            assert Settings.query.count() == 0
        resp = client.post("/api/reset")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_reset_with_no_items_still_succeeds(self, client, app):
        """Reset should succeed even if there are no shopping items."""
        with app.app_context():
            assert ShoppingItem.query.count() == 0
        resp = client.post("/api/reset")
        assert resp.status_code == 200

    def test_reset_accessible_when_locked_out(self, app):
        """A locked-out user (no session) can still call /api/reset."""
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("forgotten")))
            db.session.commit()
        locked_out = app.test_client()
        # Confirm they're locked out first
        assert locked_out.get("/api/items").status_code == 401
        # Reset succeeds
        resp = locked_out.post("/api/reset")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True
        # Now they can access the app
        assert locked_out.get("/api/items").status_code == 200

    def test_login_page_contains_forgot_password_link(self, client):
        """The login page must render a 'Forgot password?' link."""
        resp = client.get("/login")
        assert b"Forgot password" in resp.data or b"forgot" in resp.data.lower()

    def test_login_page_contains_reset_api_reference(self, client):
        """The login page JS must reference /api/reset so the button works."""
        resp = client.get("/login")
        assert b"/api/reset" in resp.data
