"""
Integration tests for the AnyList import endpoint:
  POST /api/import-anylist

All AnyList network calls are mocked via unittest.mock.patch.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from database import db, ShoppingItem, Settings


def _make_anylist_item(name, uid="item-uid-1"):
    """Return a mock AnyList item object."""
    item = MagicMock()
    item.name = name
    item.uid = uid
    return item


def _make_anylist_list(name, list_id, items):
    """Return a mock AnyList list object."""
    lst = MagicMock()
    lst.name = name
    lst.id = list_id
    lst.items = items
    return lst


class TestImportAnylist:
    """POST /api/import-anylist"""

    def test_missing_email_returns_400(self, client):
        resp = client.post(
            "/api/import-anylist",
            data=json.dumps({"password": "pass"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_missing_password_returns_400(self, client):
        resp = client.post(
            "/api/import-anylist",
            data=json.dumps({"email": "u@example.com"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_missing_both_credentials_returns_400(self, client):
        resp = client.post(
            "/api/import-anylist",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_successful_import_new_items(self, client, app):
        mock_items = [
            _make_anylist_item("Milk", "uid-1"),
            _make_anylist_item("Eggs", "uid-2"),
        ]
        mock_list = _make_anylist_list("Groceries", "list-1", mock_items)
        mock_client = MagicMock()
        mock_client.get_lists.return_value = [mock_list]

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass"}),
                content_type="application/json",
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["imported_count"] == 2
        assert data["updated_count"] == 0

    def test_successful_import_persists_items(self, client, app):
        mock_items = [_make_anylist_item("Butter", "uid-b")]
        mock_list = _make_anylist_list("Groceries", "list-1", mock_items)
        mock_client = MagicMock()
        mock_client.get_lists.return_value = [mock_list]

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass"}),
                content_type="application/json",
            )

        with app.app_context():
            item = ShoppingItem.query.filter_by(name="Butter").first()
            assert item is not None
            assert item.complete is False
            assert item.anylist_item_id == "uid-b"
            assert item.anylist_list_id == "list-1"

    def test_import_marks_existing_items_complete_before_import(self, client, app):
        """All existing items are marked complete before the import runs,
        and the new item from AnyList is imported as incomplete."""
        with app.app_context():
            db.session.add(ShoppingItem(name="OldItem", complete=False))
            db.session.commit()

        mock_items = [_make_anylist_item("NewItem", "uid-n")]
        mock_list = _make_anylist_list("Groceries", "list-1", mock_items)
        mock_client = MagicMock()
        mock_client.get_lists.return_value = [mock_list]

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass"}),
                content_type="application/json",
            )

        assert resp.status_code == 200
        with app.app_context():
            old = ShoppingItem.query.filter_by(name="OldItem").first()
            assert old.complete is True
            new = ShoppingItem.query.filter_by(name="NewItem").first()
            assert new is not None
            assert new.complete is False

    def test_import_updates_existing_item_to_incomplete(self, client, app):
        """An existing item that appears in the AnyList import is reset to incomplete."""
        with app.app_context():
            db.session.add(ShoppingItem(name="Apples", complete=True))
            db.session.commit()

        mock_items = [_make_anylist_item("Apples", "uid-a")]
        mock_list = _make_anylist_list("Groceries", "list-1", mock_items)
        mock_client = MagicMock()
        mock_client.get_lists.return_value = [mock_list]

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass"}),
                content_type="application/json",
            )

        data = resp.get_json()
        assert data["updated_count"] == 1
        assert data["imported_count"] == 0

        with app.app_context():
            item = ShoppingItem.query.filter_by(name="Apples").first()
            assert item.complete is False

    def test_import_case_insensitive_match(self, client, app):
        """Existing 'APPLES' matches AnyList item 'apples' (case-insensitive).
        The item is updated to incomplete and its AnyList IDs are set."""
        with app.app_context():
            db.session.add(ShoppingItem(name="APPLES", complete=True))
            db.session.commit()

        mock_items = [_make_anylist_item("apples", "uid-a")]
        mock_list = _make_anylist_list("Groceries", "list-1", mock_items)
        mock_client = MagicMock()
        mock_client.get_lists.return_value = [mock_list]

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass"}),
                content_type="application/json",
            )

        data = resp.get_json()
        assert data["updated_count"] == 1
        assert data["imported_count"] == 0
        with app.app_context():
            item = ShoppingItem.query.filter_by(name="APPLES").first()
            assert item.complete is False
            assert item.anylist_item_id == "uid-a"

    def test_import_by_list_name(self, client, app):
        """When list_name is provided, get_list_by_name is used and items are imported."""
        mock_items = [_make_anylist_item("Cheese", "uid-c")]
        mock_list = _make_anylist_list("Weekly", "list-w", mock_items)
        mock_client = MagicMock()
        mock_client.get_list_by_name.return_value = mock_list

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({
                    "email": "u@example.com",
                    "password": "pass",
                    "list_name": "Weekly",
                }),
                content_type="application/json",
            )

        assert resp.status_code == 200
        mock_client.get_list_by_name.assert_called_once_with("Weekly")
        # Verify the item was actually imported
        assert resp.get_json()["imported_count"] == 1
        with app.app_context():
            item = ShoppingItem.query.filter_by(name="Cheese").first()
            assert item is not None
            assert item.anylist_list_id == "list-w"

    def test_import_list_not_found_returns_400(self, client, app):
        mock_client = MagicMock()
        mock_client.get_list_by_name.return_value = None

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({
                    "email": "u@example.com",
                    "password": "pass",
                    "list_name": "NonExistent",
                }),
                content_type="application/json",
            )

        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "NonExistent" in data["error"] or "not found" in data["error"].lower()

    def test_import_no_lists_returns_400(self, client, app):
        mock_client = MagicMock()
        mock_client.get_lists.return_value = []

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass"}),
                content_type="application/json",
            )

        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_import_invalid_credentials_returns_401(self, client, app):
        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.side_effect = RuntimeError("Invalid credentials")
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "wrong"}),
                content_type="application/json",
            )

        assert resp.status_code == 401
        assert "error" in resp.get_json()

    def test_import_unauthorized_error_returns_401(self, client, app):
        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.side_effect = RuntimeError("Unauthorized access")
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "wrong"}),
                content_type="application/json",
            )

        assert resp.status_code == 401

    def test_import_generic_runtime_error_returns_400(self, client, app):
        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.side_effect = RuntimeError("Some other error")
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass"}),
                content_type="application/json",
            )

        assert resp.status_code == 400

    def test_import_unexpected_exception_returns_500(self, client, app):
        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.side_effect = Exception("Unexpected crash")
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass"}),
                content_type="application/json",
            )

        assert resp.status_code == 500

    def test_import_uses_first_list_when_no_name_given(self, client, app):
        """When list_name is empty, the first list returned is used."""
        mock_items = [_make_anylist_item("Yogurt", "uid-y")]
        first_list = _make_anylist_list("First", "list-f", mock_items)
        second_list = _make_anylist_list("Second", "list-s", [])
        mock_client = MagicMock()
        mock_client.get_lists.return_value = [first_list, second_list]

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass", "list_name": ""}),
                content_type="application/json",
            )

        assert resp.status_code == 200
        with app.app_context():
            assert ShoppingItem.query.filter_by(name="Yogurt").first() is not None

    def test_import_strips_whitespace_from_item_names(self, client, app):
        """Item names with leading/trailing whitespace are stripped."""
        mock_items = [_make_anylist_item("  Milk  ", "uid-m")]
        mock_list = _make_anylist_list("Groceries", "list-1", mock_items)
        mock_client = MagicMock()
        mock_client.get_lists.return_value = [mock_list]

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass"}),
                content_type="application/json",
            )

        with app.app_context():
            assert ShoppingItem.query.filter_by(name="Milk").first() is not None
            assert ShoppingItem.query.filter_by(name="  Milk  ").first() is None

    def test_import_total_processed_is_sum(self, client, app):
        """total_processed == imported_count + updated_count == 3."""
        with app.app_context():
            db.session.add(ShoppingItem(name="Existing", complete=True))
            db.session.commit()

        mock_items = [
            _make_anylist_item("Existing", "uid-e"),
            _make_anylist_item("New1", "uid-1"),
            _make_anylist_item("New2", "uid-2"),
        ]
        mock_list = _make_anylist_list("Groceries", "list-1", mock_items)
        mock_client = MagicMock()
        mock_client.get_lists.return_value = [mock_list]

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass"}),
                content_type="application/json",
            )

        data = resp.get_json()
        assert data["imported_count"] == 2
        assert data["updated_count"] == 1
        assert data["total_processed"] == 3

    def test_import_item_id_fallback_to_id_attr(self, client, app):
        """If item has no 'uid' attr, falls back to 'id' attr."""
        item = MagicMock(spec=["name", "id"])
        item.name = "FallbackItem"
        item.id = "fallback-id"

        mock_list = _make_anylist_list("Groceries", "list-1", [item])
        mock_client = MagicMock()
        mock_client.get_lists.return_value = [mock_list]

        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.post(
                "/api/import-anylist",
                data=json.dumps({"email": "u@example.com", "password": "pass"}),
                content_type="application/json",
            )

        assert resp.status_code == 200
        with app.app_context():
            db_item = ShoppingItem.query.filter_by(name="FallbackItem").first()
            assert db_item is not None
            assert db_item.anylist_item_id == "fallback-id"
