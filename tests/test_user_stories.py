"""
User-story based tests.

Each test class represents a complete user journey through the application,
exercising multiple endpoints in sequence to verify end-to-end behaviour.
"""
import io
import json
import time
import pytest
from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash
from database import db, ShoppingItem, Settings
from app import _sessions, _sessions_lock


def _cleanup_session(session_id):
    with _sessions_lock:
        _sessions.pop(session_id, None)


# ---------------------------------------------------------------------------
# Story 1: New user sets up the app and adds items manually
# ---------------------------------------------------------------------------

class TestStory_ManualItemManagement:
    """
    As a new user I want to add items to my shopping list manually,
    edit them, check them off, and see the list update correctly.
    """

    def test_full_manual_workflow(self, client):
        # 1. List starts empty
        resp = client.get("/api/items")
        assert resp.get_json() == []

        # 2. Add three items
        for name in ["Milk", "Eggs", "Bread"]:
            resp = client.post(
                "/api/items",
                data=json.dumps({"name": name}),
                content_type="application/json",
            )
            assert resp.status_code == 201

        # 3. Verify all three appear
        resp = client.get("/api/items")
        names = [i["name"] for i in resp.get_json()]
        assert set(names) == {"Milk", "Eggs", "Bread"}

        # 4. Edit "Bread" → "Sourdough Bread"
        items = resp.get_json()
        bread_id = next(i["id"] for i in items if i["name"] == "Bread")
        resp = client.put(
            f"/api/items/{bread_id}",
            data=json.dumps({"name": "Sourdough Bread"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Sourdough Bread"

        # 5. Check off "Milk"
        milk_id = next(i["id"] for i in client.get("/api/items").get_json() if i["name"] == "Milk")
        resp = client.put(
            f"/api/items/{milk_id}",
            data=json.dumps({"complete": True}),
            content_type="application/json",
        )
        assert resp.get_json()["complete"] is True

        # 6. Verify ordering: incomplete items first
        resp = client.get("/api/items")
        data = resp.get_json()
        complete_indices = [i for i, d in enumerate(data) if d["complete"]]
        incomplete_indices = [i for i, d in enumerate(data) if not d["complete"]]
        assert max(incomplete_indices) < min(complete_indices)

        # 7. Uncheck "Milk"
        resp = client.put(
            f"/api/items/{milk_id}",
            data=json.dumps({"complete": False}),
            content_type="application/json",
        )
        assert resp.get_json()["complete"] is False


# ---------------------------------------------------------------------------
# Story 2: User imports from AnyList, shops, items get crossed off
# ---------------------------------------------------------------------------

class TestStory_AnyListImportAndShop:
    """
    As a user I want to import my AnyList grocery list, then use the
    interactive cart assistant to add each item to my Berkeley Bowl cart,
    and have each item automatically crossed off in AnyList when done.
    """

    def test_import_then_shop_workflow(self, client, app):
        # 1. Import from AnyList
        mock_items = [
            MagicMock(name_attr="Apples", uid="uid-a"),
            MagicMock(name_attr="Bananas", uid="uid-b"),
        ]
        # MagicMock's 'name' attribute is special; set it explicitly
        mock_items[0].name = "Apples"
        mock_items[0].uid = "uid-a"
        mock_items[1].name = "Bananas"
        mock_items[1].uid = "uid-b"

        mock_list = MagicMock()
        mock_list.name = "Groceries"
        mock_list.id = "list-1"
        mock_list.items = mock_items

        mock_anylist_client = MagicMock()
        mock_anylist_client.get_lists.return_value = [mock_list]

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_anylist_client
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass"}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp.get_json()["imported_count"] == 2

        # 2. Start a cart session
        resp = client.post("/api/add-to-cart", data=json.dumps({}), content_type="application/json")
        assert resp.status_code == 200
        session_id = resp.get_json()["session_id"]

        try:
            # 3. Get status for first item
            resp = client.get(f"/api/interact/status/{session_id}")
            assert resp.status_code == 200
            first_item = resp.get_json()["item"]
            assert first_item["name"] in ("Apples", "Bananas")

            # 4. Mark first item complete (with AnyList cross-off mocked)
            with app.app_context():
                item_id = ShoppingItem.query.filter_by(name=first_item["name"]).first().id

            mock_anylist_client2 = MagicMock()
            with patch("pyanylist.AnyListClient") as MockCls2:
                MockCls2.login.return_value = mock_anylist_client2
                resp = client.post(
                    f"/api/interact/item-complete/{session_id}",
                    data=json.dumps({"product_url": ""}),
                    content_type="application/json",
                )
            assert resp.status_code == 200
            assert resp.get_json()["success"] is True

            # 5. Verify item is complete in DB
            with app.app_context():
                assert ShoppingItem.query.get(item_id).complete is True

            # 6. Skip second item
            resp = client.post(
                f"/api/interact/item-skip/{session_id}",
                data=json.dumps({}),
                content_type="application/json",
            )
            assert resp.get_json()["session_complete"] is True

        finally:
            _cleanup_session(session_id)


# ---------------------------------------------------------------------------
# Story 3: User protects the app with a password
# ---------------------------------------------------------------------------

class TestStory_PasswordProtection:
    """
    As a user I want to set a password so that only I can access the app.
    """

    def test_set_password_then_login_logout(self, client, app):
        # 1. No password → access is open
        resp = client.get("/api/items")
        assert resp.status_code == 200

        # 2. Set a password
        resp = client.post(
            "/api/settings/password",
            data=json.dumps({"password": "mysecret"}),
            content_type="application/json",
        )
        assert resp.get_json()["has_password"] is True

        # 3. Now unauthenticated access is blocked
        unauth = app.test_client()
        resp = unauth.get("/api/items")
        assert resp.status_code == 401

        # 4. Login with correct password
        resp = client.post("/login", data={"password": "mysecret"})
        assert resp.status_code == 302

        # 5. Authenticated access works
        resp = client.get("/api/items")
        assert resp.status_code == 200

        # 6. Logout
        resp = client.get("/logout")
        assert resp.status_code == 302

        # 7. After logout, access is blocked again
        resp = client.get("/api/items")
        assert resp.status_code == 401

    def test_wrong_password_cannot_access(self, client, app):
        client.post(
            "/api/settings/password",
            data=json.dumps({"password": "correct"}),
            content_type="application/json",
        )
        unauth = app.test_client()
        unauth.post("/login", data={"password": "wrong"})
        resp = unauth.get("/api/items")
        assert resp.status_code == 401

    def test_clear_password_reopens_access(self, app):
        # Set a password directly in the DB
        from werkzeug.security import generate_password_hash
        from database import Settings
        with app.app_context():
            db.session.add(Settings(app_password=generate_password_hash("temp")))
            db.session.commit()
        # Clear it using an authenticated client
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
        # Now unauthenticated access is open again
        unauth = app.test_client()
        resp = unauth.get("/api/items")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Story 4: User backs up and restores their list via CSV
# ---------------------------------------------------------------------------

class TestStory_CsvBackupRestore:
    """
    As a user I want to export my shopping list to CSV for backup,
    and later restore it by importing the same CSV.
    """

    def test_backup_and_restore(self, client, app):
        # 1. Build a list
        items_to_add = [
            {"name": "Olive Oil", "url": "https://example.com/oil"},
            {"name": "Pasta", "url": ""},
            {"name": "Tomatoes", "url": "https://example.com/tomatoes"},
        ]
        for item in items_to_add:
            client.post("/api/items", data=json.dumps(item), content_type="application/json")

        # Mark one complete
        with app.app_context():
            pasta = ShoppingItem.query.filter_by(name="Pasta").first()
            pasta.complete = True
            db.session.commit()

        # 2. Export
        export_resp = client.get("/api/export-csv")
        assert export_resp.status_code == 200
        csv_data = export_resp.data

        # 3. Wipe the DB
        with app.app_context():
            ShoppingItem.query.delete()
            db.session.commit()

        assert client.get("/api/items").get_json() == []

        # 4. Restore from CSV
        import_resp = client.post(
            "/api/import-csv",
            data={"file": (io.BytesIO(csv_data), "backup.csv")},
            content_type="multipart/form-data",
        )
        assert import_resp.status_code == 200
        result = import_resp.get_json()
        assert result["imported_count"] == 3

        # 5. Verify restored items
        resp = client.get("/api/items")
        names = {i["name"] for i in resp.get_json()}
        assert names == {"Olive Oil", "Pasta", "Tomatoes"}

        # 6. Verify complete status preserved
        with app.app_context():
            assert ShoppingItem.query.filter_by(name="Pasta").first().complete is True
            assert ShoppingItem.query.filter_by(name="Olive Oil").first().complete is False


# ---------------------------------------------------------------------------
# Story 5: User saves AnyList settings and they persist
# ---------------------------------------------------------------------------

class TestStory_SettingsPersistence:
    """
    As a user I want to save my AnyList credentials in Settings so I don't
    have to re-enter them every time I import.
    """

    def test_settings_saved_and_retrieved(self, client):
        # 1. Save settings
        resp = client.post(
            "/api/settings",
            data=json.dumps({
                "anylist_email": "shopper@example.com",
                "anylist_password": "grocerypass",
                "anylist_list_name": "Weekly Groceries",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200

        # 2. Retrieve settings
        resp = client.get("/api/settings")
        data = resp.get_json()
        assert data["anylist_email"] == "shopper@example.com"
        assert data["anylist_password"] == "grocerypass"
        assert data["anylist_list_name"] == "Weekly Groceries"

    def test_partial_settings_update_preserves_other_fields(self, client):
        # 1. Save all fields
        client.post(
            "/api/settings",
            data=json.dumps({
                "anylist_email": "a@b.com",
                "anylist_password": "pass1",
                "anylist_list_name": "List1",
            }),
            content_type="application/json",
        )

        # 2. Update only the list name
        client.post(
            "/api/settings",
            data=json.dumps({"anylist_list_name": "List2"}),
            content_type="application/json",
        )

        # 3. Other fields unchanged
        resp = client.get("/api/settings")
        data = resp.get_json()
        assert data["anylist_email"] == "a@b.com"
        assert data["anylist_password"] == "pass1"
        assert data["anylist_list_name"] == "List2"


# ---------------------------------------------------------------------------
# Story 6: User adds a URL to an item and it is used in the cart session
# ---------------------------------------------------------------------------

class TestStory_ItemUrlUsedInCartSession:
    """
    As a user I want to save a product URL for an item so that the cart
    assistant navigates directly to the product page instead of searching.
    """

    def test_item_with_url_gets_navigate_action(self, client, app):
        # 1. Add item with URL
        resp = client.post(
            "/api/items",
            data=json.dumps({
                "name": "Organic Milk",
                "url": "https://shop.berkeleybowl.com/product/organic-milk",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 201

        # 2. Start cart session
        resp = client.post("/api/add-to-cart", data=json.dumps({}), content_type="application/json")
        session_id = resp.get_json()["session_id"]

        try:
            # 3. Check status — should be 'ready' with navigate action
            resp = client.get(f"/api/interact/status/{session_id}")
            data = resp.get_json()
            assert data["status"] == "ready"
            assert data["action"] == "navigate"
            assert data["url"] == "https://shop.berkeleybowl.com/product/organic-milk"
        finally:
            _cleanup_session(session_id)

    def test_item_without_url_gets_search_action(self, client, app):
        # 1. Add item without URL
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "Free Range Eggs"}),
            content_type="application/json",
        )
        assert resp.status_code == 201

        # 2. Start cart session
        resp = client.post("/api/add-to-cart", data=json.dumps({}), content_type="application/json")
        session_id = resp.get_json()["session_id"]

        try:
            # 3. Check status — should be 'search_needed'
            resp = client.get(f"/api/interact/status/{session_id}")
            data = resp.get_json()
            assert data["status"] == "search_needed"
            assert data["search_query"] == "Free Range Eggs"
        finally:
            _cleanup_session(session_id)

    def test_completing_item_saves_product_url(self, client, app):
        """When user completes an item on a product page, the URL is saved for next time."""
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "Sourdough"}),
            content_type="application/json",
        )
        item_id = resp.get_json()["id"]

        resp = client.post("/api/add-to-cart", data=json.dumps({}), content_type="application/json")
        session_id = resp.get_json()["session_id"]

        try:
            product_url = "https://shop.berkeleybowl.com/product/sourdough-loaf"
            client.post(
                f"/api/interact/item-complete/{session_id}",
                data=json.dumps({"product_url": product_url}),
                content_type="application/json",
            )

            with app.app_context():
                item = ShoppingItem.query.get(item_id)
                assert item.url == product_url
        finally:
            _cleanup_session(session_id)
