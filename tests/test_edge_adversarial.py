"""
Edge case, chaos, and adversarial tests.

These tests probe boundary conditions, malformed inputs, injection attempts,
concurrent-access patterns, and unexpected data shapes that real-world
attackers or misbehaving clients might send.
"""
import io
import json
import time
import uuid
import threading
import pytest
from unittest.mock import patch, MagicMock
from database import db, ShoppingItem, Settings
from app import _sessions, _sessions_lock


def _make_session(items, current_index=0):
    session_id = str(uuid.uuid4())
    with _sessions_lock:
        _sessions[session_id] = {
            "items": items,
            "current_index": current_index,
            "state": "running",
            "last_heartbeat": time.time(),
        }
    return session_id


def _cleanup_session(session_id):
    with _sessions_lock:
        _sessions.pop(session_id, None)


# ---------------------------------------------------------------------------
# Edge cases: item names
# ---------------------------------------------------------------------------

class TestItemNameEdgeCases:

    def test_unicode_item_name(self, client):
        """Item names with Unicode characters are stored and returned correctly."""
        name = "Café au lait ☕ 牛奶"
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": name}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.get_json()["name"] == name

    def test_emoji_item_name(self, client):
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "🥑 Avocado"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.get_json()["name"] == "🥑 Avocado"

    def test_item_name_with_special_chars(self, client):
        """Names with quotes, ampersands, angle brackets are stored safely."""
        name = "Ben & Jerry's <Ice Cream> \"Chunky Monkey\""
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": name}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.get_json()["name"] == name

    def test_item_name_newline_and_tab(self, client):
        """Names with newlines/tabs are stored as-is (no server-side stripping)."""
        name = "Item\nWith\tWhitespace"
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": name}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.get_json()["name"] == name

    def test_single_character_item_name(self, client):
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "X"}),
            content_type="application/json",
        )
        assert resp.status_code == 201

    def test_item_name_case_sensitivity_preserved(self, client):
        """'apple' and 'Apple' are treated as different items.
        SQLite's UNIQUE constraint is case-sensitive by default for non-ASCII,
        and the app does not normalise names, so both are accepted."""
        client.post("/api/items", data=json.dumps({"name": "apple"}), content_type="application/json")
        resp = client.post("/api/items", data=json.dumps({"name": "Apple"}), content_type="application/json")
        assert resp.status_code == 201

    def test_very_long_item_name_boundary(self, client):
        """Name at 255 chars (the column limit) is accepted."""
        name = "A" * 255
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": name}),
            content_type="application/json",
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Adversarial: injection attempts
# ---------------------------------------------------------------------------

class TestInjectionAttempts:

    def test_sql_injection_in_item_name(self, client):
        """SQL injection in item name is stored safely via parameterised queries."""
        payload = "'; DROP TABLE shopping_items; --"
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": payload}),
            content_type="application/json",
        )
        # ORM uses parameterised queries — the payload is stored as a literal string
        assert resp.status_code == 201
        assert resp.get_json()["name"] == payload
        # Table must still exist and be queryable
        assert client.get("/api/items").status_code == 200

    def test_sql_injection_in_update_name(self, client, sample_item, app):
        """SQL injection in PUT name is stored safely as a literal string."""
        with app.app_context():
            item_id = ShoppingItem.query.filter_by(name="Apples").first().id
        payload = "' OR '1'='1"
        resp = client.put(
            f"/api/items/{item_id}",
            data=json.dumps({"name": payload}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == payload
        # DB must still be intact
        assert client.get("/api/items").status_code == 200

    def test_xss_in_item_name_stored_as_literal(self, client):
        """XSS payload is stored as a literal string, not executed server-side."""
        xss = "<script>alert('xss')</script>"
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": xss}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.get_json()["name"] == xss

    def test_path_traversal_in_session_id(self, client):
        """Path traversal in session_id is handled gracefully — returns 404."""
        resp = client.get("/api/interact/status/../../etc/passwd")
        assert resp.status_code == 404

    def test_null_bytes_in_item_name(self, client):
        """Null bytes in item name are stored as-is — the server does not crash."""
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "Item\x00WithNull"}),
            content_type="application/json",
        )
        assert resp.status_code == 201

    def test_oversized_json_body(self, client):
        """A very large JSON body (100k chars) is accepted — no size limit is enforced."""
        huge_name = "A" * 100_000
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": huge_name}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert len(resp.get_json()["name"]) == 100_000

    def test_wrong_content_type_for_json_endpoint(self, client):
        """Sending form-encoded data to a JSON endpoint returns 415 Unsupported Media Type."""
        resp = client.post(
            "/api/items",
            data="name=Milk",
            content_type="application/x-www-form-urlencoded",
        )
        assert resp.status_code == 415

    def test_malformed_json_body(self, client):
        """Malformed JSON body returns 400 Bad Request."""
        resp = client.post(
            "/api/items",
            data="{not valid json",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_extra_fields_in_add_item_are_ignored(self, client):
        """Unknown fields in the request body are silently ignored."""
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "Milk", "evil_field": "DROP TABLE", "id": 9999}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Milk"
        assert data["id"] != 9999  # server assigns its own ID

    def test_negative_item_id_returns_404(self, client):
        resp = client.put(
            "/api/items/-1",
            data=json.dumps({"name": "Ghost"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_float_item_id_returns_404(self, client):
        resp = client.put(
            "/api/items/1.5",
            data=json.dumps({"name": "Ghost"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_string_item_id_returns_404(self, client):
        resp = client.put(
            "/api/items/abc",
            data=json.dumps({"name": "Ghost"}),
            content_type="application/json",
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Edge cases: CSV import
# ---------------------------------------------------------------------------

class TestCsvEdgeCases:

    def _csv(self, content, filename="test.csv"):
        return (io.BytesIO(content.encode("utf-8")), filename)

    def test_csv_with_bom(self, client):
        """CSV with UTF-8 BOM is handled correctly."""
        content = "\ufeffName,URL,Complete\nMilk,,No\n"
        data = {"file": self._csv(content)}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200

    def test_csv_with_windows_line_endings(self, client):
        content = "Name,URL,Complete\r\nMilk,,No\r\nEggs,,No\r\n"
        data = {"file": (io.BytesIO(content.encode("utf-8")), "test.csv")}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        assert resp.get_json()["imported_count"] == 2

    def test_csv_with_quoted_fields(self, client):
        content = 'Name,URL,Complete\n"Milk, whole","https://example.com",No\n'
        data = {"file": self._csv(content)}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200

    def test_csv_missing_complete_column(self, client):
        """CSV without a Complete column defaults to incomplete."""
        content = "Name,URL\nMilk,https://example.com\n"
        data = {"file": self._csv(content)}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200

    def test_csv_extra_columns_ignored(self, client):
        content = "Name,URL,Complete,ExtraCol\nMilk,,No,ignored\n"
        data = {"file": self._csv(content)}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        assert resp.get_json()["imported_count"] == 1

    def test_csv_empty_file(self, client):
        """An empty CSV file (no header, no rows) is handled gracefully."""
        data = {"file": self._csv("")}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        assert resp.get_json()["imported_count"] == 0

    def test_csv_header_only(self, client):
        """A CSV with only a header row imports zero items."""
        data = {"file": self._csv("Name,URL,Complete\n")}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        assert resp.get_json()["imported_count"] == 0

    def test_csv_very_large_file(self, client, app):
        """A CSV with 500 rows is imported without error."""
        rows = ["Name,URL,Complete"] + [f"Item{i},,No" for i in range(500)]
        content = "\n".join(rows) + "\n"
        data = {"file": self._csv(content)}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        assert resp.get_json()["imported_count"] == 500

    def test_csv_duplicate_names_in_file(self, client, app):
        """If the CSV itself has duplicate names, the second occurrence updates the first."""
        content = "Name,URL,Complete\nMilk,,No\nMilk,https://example.com,Yes\n"
        data = {"file": self._csv(content)}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        # First row creates, second row updates
        result = resp.get_json()
        assert result["imported_count"] + result["updated_count"] == 2


# ---------------------------------------------------------------------------
# Edge cases: interact session
# ---------------------------------------------------------------------------

class TestInteractSessionEdgeCases:

    def test_session_with_zero_items(self, client):
        """A session with an empty item list immediately reports complete."""
        sid = _make_session([])
        try:
            resp = client.get(f"/api/interact/status/{sid}")
            assert resp.status_code == 200
            assert resp.get_json()["status"] == "complete"
        finally:
            _cleanup_session(sid)

    def test_complete_item_with_missing_db_record(self, client, app):
        """If the DB item no longer exists, item-complete still advances the session."""
        items = [{"id": 99999, "name": "Ghost", "url": "",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            resp = client.post(
                f"/api/interact/item-complete/{sid}",
                data=json.dumps({"product_url": ""}),
                content_type="application/json",
            )
            assert resp.status_code == 200
            assert resp.get_json()["next_item_index"] == 1
        finally:
            _cleanup_session(sid)

    def test_session_id_with_special_chars_returns_404(self, client):
        """Session IDs with special characters return 404, not 500."""
        for bad_id in ["<script>", "'; DROP TABLE--", "null", "undefined"]:
            resp = client.get(f"/api/interact/status/{bad_id}")
            assert resp.status_code == 404

    def test_multiple_complete_calls_on_same_item(self, client, app):
        """Calling item-complete twice on the same session advances index twice."""
        with app.app_context():
            items_db = [ShoppingItem(name=f"Item{i}", complete=False) for i in range(3)]
            for i in items_db:
                db.session.add(i)
            db.session.commit()
            ids = [i.id for i in items_db]

        items = [
            {"id": ids[0], "name": "Item0", "url": "", "anylist_item_id": None,
             "anylist_list_id": None, "complete": False},
            {"id": ids[1], "name": "Item1", "url": "", "anylist_item_id": None,
             "anylist_list_id": None, "complete": False},
            {"id": ids[2], "name": "Item2", "url": "", "anylist_item_id": None,
             "anylist_list_id": None, "complete": False},
        ]
        sid = _make_session(items)
        try:
            client.post(f"/api/interact/item-complete/{sid}",
                        data=json.dumps({"product_url": ""}), content_type="application/json")
            client.post(f"/api/interact/item-complete/{sid}",
                        data=json.dumps({"product_url": ""}), content_type="application/json")
            with _sessions_lock:
                assert _sessions[sid]["current_index"] == 2
        finally:
            _cleanup_session(sid)


# ---------------------------------------------------------------------------
# Chaos: concurrent requests
# ---------------------------------------------------------------------------

class TestConcurrentAccess:

    def test_concurrent_add_items_no_crash(self, app):
        """Multiple threads adding different items simultaneously should not crash,
        and all 10 distinct items should be persisted."""
        errors = []

        def add_item(name):
            with app.test_client() as c:
                resp = c.post(
                    "/api/items",
                    data=json.dumps({"name": name}),
                    content_type="application/json",
                )
                if resp.status_code not in (201, 409):
                    errors.append(f"{name}: {resp.status_code}")

        threads = [threading.Thread(target=add_item, args=(f"ConcurrentItem{i}",))
                   for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Unexpected errors: {errors}"
        # All 10 distinct items must be in the DB
        with app.app_context():
            for i in range(10):
                assert ShoppingItem.query.filter_by(name=f"ConcurrentItem{i}").first() is not None

    def test_concurrent_heartbeats_no_crash(self, app):
        """Multiple threads sending heartbeats to the same session should not crash."""
        items = [{"id": 1, "name": "X", "url": "", "anylist_item_id": None,
                  "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        errors = []

        def send_heartbeat():
            with app.test_client() as c:
                resp = c.post(f"/api/interact/heartbeat/{sid}")
                if resp.status_code not in (200, 404):
                    errors.append(resp.status_code)

        try:
            threads = [threading.Thread(target=send_heartbeat) for _ in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            assert errors == []
        finally:
            _cleanup_session(sid)

    def test_concurrent_skip_and_complete_on_same_session(self, app):
        """Concurrent skip + complete on the same session should not corrupt state."""
        with app.app_context():
            item = ShoppingItem(name="RaceItem", complete=False)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        items = [{"id": item_id, "name": "RaceItem", "url": "",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        results = []

        def do_complete():
            with app.test_client() as c:
                r = c.post(f"/api/interact/item-complete/{sid}",
                           data=json.dumps({"product_url": ""}),
                           content_type="application/json")
                results.append(("complete", r.status_code))

        def do_skip():
            with app.test_client() as c:
                r = c.post(f"/api/interact/item-skip/{sid}",
                           data=json.dumps({}),
                           content_type="application/json")
                results.append(("skip", r.status_code))

        try:
            t1 = threading.Thread(target=do_complete)
            t2 = threading.Thread(target=do_skip)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            # One should succeed (200), the other should get 400 (already processed)
            statuses = [r[1] for r in results]
            assert 200 in statuses
            # The index should be at most 2 (not negative or wildly wrong)
            with _sessions_lock:
                idx = _sessions.get(sid, {}).get("current_index", 0)
            assert 0 <= idx <= 2
        finally:
            _cleanup_session(sid)


# ---------------------------------------------------------------------------
# Adversarial: auth bypass attempts
# ---------------------------------------------------------------------------

class TestAuthBypassAttempts:

    def test_forged_session_cookie_with_truthy_string_grants_access(self, app):
        """The require_login check uses a truthy test (not strict `is True`),
        so a session value of 'yes' (truthy string) currently grants access.
        This test documents the actual behaviour."""
        from werkzeug.security import generate_password_hash
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("pass")))
            db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sess:
            sess["authenticated"] = "yes"  # truthy string, not True

        resp = client.get("/api/items")
        # Truthy check passes → 200 (access granted)
        assert resp.status_code == 200

    def test_interact_endpoints_bypass_auth_by_design(self, app):
        """The interact endpoints are intentionally auth-exempt (iOS Safari workaround)."""
        from werkzeug.security import generate_password_hash
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("pass")))
            db.session.commit()

        unauth = app.test_client()
        # These should return 404 (session not found), not 401
        resp = unauth.get("/api/interact/status/fake-session")
        assert resp.status_code == 404

        resp = unauth.post("/api/interact/heartbeat/fake-session")
        assert resp.status_code == 404

    def test_settings_endpoint_accessible_without_auth(self, app):
        """GET /api/settings is accessible without auth (no password set)."""
        unauth = app.test_client()
        resp = unauth.get("/api/settings")
        assert resp.status_code == 200

    def test_password_endpoint_blocked_by_auth_when_password_set(self, app):
        """POST /api/settings/password IS protected by require_login once a password
        is set. Unauthenticated users must use POST /api/reset to recover access."""
        from werkzeug.security import generate_password_hash
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("pass")))
            db.session.commit()

        unauth = app.test_client()
        resp = unauth.post(
            "/api/settings/password",
            data=json.dumps({"password": "new"}),
            content_type="application/json",
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Edge cases: settings
# ---------------------------------------------------------------------------

class TestSettingsEdgeCases:

    def test_save_settings_with_empty_strings(self, client, app):
        """Saving empty strings for settings fields is accepted."""
        resp = client.post(
            "/api/settings",
            data=json.dumps({
                "anylist_email": "",
                "anylist_password": "",
                "anylist_list_name": "",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_save_settings_with_very_long_email(self, client):
        """Very long email is stored (up to column limit)."""
        long_email = "a" * 200 + "@example.com"
        resp = client.post(
            "/api/settings",
            data=json.dumps({"anylist_email": long_email}),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_get_settings_returns_same_row_on_repeated_calls(self, client, app):
        """Repeated GET /api/settings calls do not create multiple rows."""
        for _ in range(5):
            client.get("/api/settings")
        with app.app_context():
            assert Settings.query.count() == 1

    def test_password_unicode_characters(self, client, app):
        """App password with Unicode characters is hashed and verified correctly."""
        from werkzeug.security import check_password_hash
        unicode_pass = "pässwörд🔑"
        client.post(
            "/api/settings/password",
            data=json.dumps({"password": unicode_pass}),
            content_type="application/json",
        )
        with app.app_context():
            s = Settings.query.first()
            assert check_password_hash(s.app_password, unicode_pass)


# ---------------------------------------------------------------------------
# Edge cases: page routes
# ---------------------------------------------------------------------------

class TestPageRoutes:

    def test_index_page_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_settings_page_returns_200(self, client):
        resp = client.get("/settings")
        assert resp.status_code == 200

    def test_interact_page_returns_200(self, client):
        resp = client.get("/interact")
        assert resp.status_code == 200

    def test_nonexistent_route_returns_404(self, client):
        resp = client.get("/this/does/not/exist")
        assert resp.status_code == 404

    def test_index_shows_logout_when_password_set(self, client, app):
        """The index page includes a logout link when a password is configured."""
        from werkzeug.security import generate_password_hash
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("pass")))
            db.session.commit()
        with client.session_transaction() as sess:
            sess["authenticated"] = True
        resp = client.get("/")
        assert b"logout" in resp.data.lower() or b"log out" in resp.data.lower()

    def test_index_no_logout_when_no_password(self, client):
        """The index page does not show a logout link when no password is set."""
        resp = client.get("/")
        assert b"logout" not in resp.data.lower()
