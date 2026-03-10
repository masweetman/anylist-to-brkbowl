"""
Integration tests for shopping item API endpoints:
  GET  /api/items
  POST /api/items
  PUT  /api/items/<id>
"""
import json
import pytest
from database import db, ShoppingItem


class TestGetItems:
    """GET /api/items"""

    def test_returns_empty_list_when_no_items(self, client):
        resp = client.get("/api/items")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_all_items(self, client, sample_items):
        resp = client.get("/api/items")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 4

    def test_response_is_json(self, client):
        resp = client.get("/api/items")
        assert resp.content_type == "application/json"

    def test_item_shape(self, client, sample_item):
        resp = client.get("/api/items")
        data = resp.get_json()
        assert len(data) == 1
        item = data[0]
        assert "id" in item
        assert "name" in item
        assert "complete" in item
        assert "url" in item
        assert "anylist_item_id" in item
        assert "anylist_list_id" in item
        assert "created_at" in item
        assert "updated_at" in item

    def test_incomplete_items_appear_before_complete(self, client, sample_items):
        """Items are ordered: incomplete first, then complete."""
        resp = client.get("/api/items")
        data = resp.get_json()
        # Find the index of the first complete item
        complete_indices = [i for i, d in enumerate(data) if d["complete"]]
        incomplete_indices = [i for i, d in enumerate(data) if not d["complete"]]
        if complete_indices and incomplete_indices:
            assert max(incomplete_indices) < min(complete_indices)

    def test_no_auth_required_when_no_password_set(self, no_password_client):
        """When no app password is configured, unauthenticated access is allowed."""
        resp = no_password_client.get("/api/items")
        assert resp.status_code == 200

    def test_auth_required_when_password_set(self, auth_client, app):
        """When a password is set, unauthenticated requests to /api/items get 401."""
        # Use a fresh unauthenticated client against the same app that has a password
        unauth = app.test_client()
        resp = unauth.get("/api/items")
        assert resp.status_code == 401


class TestAddItem:
    """POST /api/items"""

    def test_add_item_success(self, client):
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "Milk"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Milk"
        assert data["complete"] is False

    def test_add_item_with_url(self, client):
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "Milk", "url": "https://example.com/milk"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.get_json()["url"] == "https://example.com/milk"

    def test_add_item_returns_id(self, client):
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "Eggs"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert isinstance(resp.get_json()["id"], int)

    def test_add_item_missing_name_returns_400(self, client):
        resp = client.post(
            "/api/items",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_add_item_empty_name_returns_400(self, client):
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_add_item_null_body_returns_400(self, client):
        resp = client.post(
            "/api/items",
            data="null",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_add_duplicate_item_returns_409(self, client, sample_item):
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "Apples"}),
            content_type="application/json",
        )
        assert resp.status_code == 409
        assert "error" in resp.get_json()

    def test_add_item_persisted_in_db(self, client, app):
        client.post(
            "/api/items",
            data=json.dumps({"name": "Persisted"}),
            content_type="application/json",
        )
        with app.app_context():
            item = ShoppingItem.query.filter_by(name="Persisted").first()
            assert item is not None

    def test_add_item_url_defaults_to_empty_string(self, client):
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "NoURL"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        # url should be empty string (as passed) or None — not an error
        data = resp.get_json()
        assert data.get("url") in ("", None)

    def test_add_item_complete_defaults_to_false(self, client):
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "DefaultComplete"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.get_json()["complete"] is False

    def test_add_item_name_whitespace_only_is_accepted(self, client):
        """The API checks data.get('name') which is truthy for whitespace strings,
        so whitespace-only names are currently accepted with 201.
        This test documents the actual behaviour and will catch any regression."""
        resp = client.post(
            "/api/items",
            data=json.dumps({"name": "   "}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        # The name is stored as-is (whitespace preserved)
        assert resp.get_json()["name"] == "   "


class TestUpdateItem:
    """PUT /api/items/<id>"""

    def test_update_name(self, client, sample_item, app):
        with app.app_context():
            item_id = ShoppingItem.query.filter_by(name="Apples").first().id
        resp = client.put(
            f"/api/items/{item_id}",
            data=json.dumps({"name": "Green Apples"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Green Apples"

    def test_update_url(self, client, sample_item, app):
        with app.app_context():
            item_id = ShoppingItem.query.filter_by(name="Apples").first().id
        resp = client.put(
            f"/api/items/{item_id}",
            data=json.dumps({"url": "https://new.example.com"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["url"] == "https://new.example.com"

    def test_mark_complete(self, client, sample_item, app):
        with app.app_context():
            item_id = ShoppingItem.query.filter_by(name="Apples").first().id
        resp = client.put(
            f"/api/items/{item_id}",
            data=json.dumps({"complete": True}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["complete"] is True

    def test_mark_incomplete(self, client, app):
        with app.app_context():
            item = ShoppingItem(name="Done", complete=True)
            db.session.add(item)
            db.session.commit()
            item_id = item.id
        resp = client.put(
            f"/api/items/{item_id}",
            data=json.dumps({"complete": False}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["complete"] is False

    def test_update_nonexistent_item_returns_404(self, client):
        resp = client.put(
            "/api/items/99999",
            data=json.dumps({"name": "Ghost"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_update_name_to_existing_name_returns_409(self, client, sample_items, app):
        with app.app_context():
            apple_id = ShoppingItem.query.filter_by(name="Apples").first().id
        resp = client.put(
            f"/api/items/{apple_id}",
            data=json.dumps({"name": "Bananas"}),
            content_type="application/json",
        )
        assert resp.status_code == 409

    def test_update_name_to_same_name_is_ok(self, client, sample_item, app):
        """Updating an item's name to its own current name should succeed."""
        with app.app_context():
            item_id = ShoppingItem.query.filter_by(name="Apples").first().id
        resp = client.put(
            f"/api/items/{item_id}",
            data=json.dumps({"name": "Apples"}),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_update_persisted_in_db(self, client, sample_item, app):
        with app.app_context():
            item_id = ShoppingItem.query.filter_by(name="Apples").first().id
        client.put(
            f"/api/items/{item_id}",
            data=json.dumps({"name": "Pears"}),
            content_type="application/json",
        )
        with app.app_context():
            assert ShoppingItem.query.filter_by(name="Pears").first() is not None
            assert ShoppingItem.query.filter_by(name="Apples").first() is None

    def test_update_complete_syncs_without_anylist_ids(self, client, sample_item, app):
        """Toggling complete on an item without AnyList IDs should not error."""
        with app.app_context():
            item_id = ShoppingItem.query.filter_by(name="Apples").first().id
        resp = client.put(
            f"/api/items/{item_id}",
            data=json.dumps({"complete": True}),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_update_complete_with_anylist_ids_calls_cross_off(self, client, app):
        """When item has AnyList IDs and settings, cross_off_item is called."""
        from unittest.mock import patch, MagicMock
        from database import Settings

        with app.app_context():
            item = ShoppingItem(
                name="AnyListItem",
                complete=False,
                anylist_item_id="item-abc",
                anylist_list_id="list-xyz",
            )
            db.session.add(item)
            settings = Settings(
                anylist_email="u@example.com",
                anylist_password="pass",
            )
            db.session.add(settings)
            db.session.commit()
            item_id = item.id

        mock_client = MagicMock()
        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.put(
                f"/api/items/{item_id}",
                data=json.dumps({"complete": True}),
                content_type="application/json",
            )

        assert resp.status_code == 200
        mock_client.cross_off_item.assert_called_once_with("list-xyz", "item-abc")

    def test_update_uncheck_with_anylist_ids_calls_uncheck(self, client, app):
        """When item has AnyList IDs and settings, uncheck_item is called on False."""
        from unittest.mock import patch, MagicMock
        from database import Settings

        with app.app_context():
            item = ShoppingItem(
                name="AnyListItem2",
                complete=True,
                anylist_item_id="item-abc2",
                anylist_list_id="list-xyz2",
            )
            db.session.add(item)
            settings = Settings(
                anylist_email="u@example.com",
                anylist_password="pass",
            )
            db.session.add(settings)
            db.session.commit()
            item_id = item.id

        mock_client = MagicMock()
        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.put(
                f"/api/items/{item_id}",
                data=json.dumps({"complete": False}),
                content_type="application/json",
            )

        assert resp.status_code == 200
        mock_client.uncheck_item.assert_called_once_with("list-xyz2", "item-abc2")

    def test_anylist_sync_failure_does_not_fail_request(self, client, app):
        """If AnyList sync raises, the PUT still returns 200."""
        from unittest.mock import patch, MagicMock
        from database import Settings

        with app.app_context():
            item = ShoppingItem(
                name="SyncFail",
                complete=False,
                anylist_item_id="item-fail",
                anylist_list_id="list-fail",
            )
            db.session.add(item)
            settings = Settings(anylist_email="u@example.com", anylist_password="pass")
            db.session.add(settings)
            db.session.commit()
            item_id = item.id

        mock_client = MagicMock()
        mock_client.cross_off_item.side_effect = Exception("Network error")
        with patch("pyanylist.AnyListClient") as MockCls:
            MockCls.login.return_value = mock_client
            resp = client.put(
                f"/api/items/{item_id}",
                data=json.dumps({"complete": True}),
                content_type="application/json",
            )

        assert resp.status_code == 200
