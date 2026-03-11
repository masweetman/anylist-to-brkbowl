"""
Integration tests for the interactive cart session API:
  GET  /api/interact/status/<session_id>
  POST /api/interact/item-complete/<session_id>
  POST /api/interact/item-skip/<session_id>
  POST /api/interact/heartbeat/<session_id>
  POST /api/add-to-cart
"""
import json
import time
import uuid
import pytest
from database import db, ShoppingItem, Settings, InteractSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(items, current_index=0):
    """Insert a session directly into the database and return its ID."""
    session_id = str(uuid.uuid4())
    sess = InteractSession(
        id=session_id,
        items=items,
        current_index=current_index,
        state='running',
        last_heartbeat=time.time(),
    )
    db.session.add(sess)
    db.session.commit()
    return session_id


def _cleanup_session(session_id):
    InteractSession.query.filter_by(id=session_id).delete()
    db.session.commit()


# ---------------------------------------------------------------------------
# GET /api/interact/status/<session_id>
# ---------------------------------------------------------------------------

class TestInteractStatus:

    def test_unknown_session_returns_404(self, client):
        resp = client.get("/api/interact/status/nonexistent-id")
        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_status_ready_when_item_has_url(self, client, app):
        items = [{"id": 1, "name": "Apples", "url": "https://example.com/apples",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            resp = client.get(f"/api/interact/status/{sid}")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "ready"
            assert data["action"] == "navigate"
            assert data["url"] == "https://example.com/apples"
            assert data["item"]["name"] == "Apples"
            assert data["item_number"] == 1
            assert data["total_items"] == 1
        finally:
            _cleanup_session(sid)

    def test_status_search_needed_when_no_url(self, client, app):
        items = [{"id": 2, "name": "Bananas", "url": "",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            resp = client.get(f"/api/interact/status/{sid}")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "search_needed"
            assert data["action"] == "search"
            assert data["search_query"] == "Bananas"
        finally:
            _cleanup_session(sid)

    def test_status_complete_when_all_items_processed(self, client, app):
        items = [{"id": 1, "name": "Apples", "url": "https://example.com",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items, current_index=1)  # past the end
        try:
            resp = client.get(f"/api/interact/status/{sid}")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "complete"
        finally:
            _cleanup_session(sid)

    def test_status_updates_heartbeat(self, client, app):
        items = [{"id": 1, "name": "X", "url": "https://x.com",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            old_hb = InteractSession.query.get(sid).last_heartbeat
            time.sleep(0.01)
            client.get(f"/api/interact/status/{sid}")
            new_hb = InteractSession.query.get(sid).last_heartbeat
            assert new_hb >= old_hb
        finally:
            _cleanup_session(sid)

    def test_status_item_number_increments(self, client, app):
        items = [
            {"id": 1, "name": "A", "url": "https://a.com",
             "anylist_item_id": None, "anylist_list_id": None, "complete": False},
            {"id": 2, "name": "B", "url": "https://b.com",
             "anylist_item_id": None, "anylist_list_id": None, "complete": False},
        ]
        sid = _make_session(items, current_index=1)
        try:
            resp = client.get(f"/api/interact/status/{sid}")
            data = resp.get_json()
            assert data["item_number"] == 2
            assert data["total_items"] == 2
        finally:
            _cleanup_session(sid)

    def test_status_empty_url_string_triggers_search(self, client, app):
        """An item with url='' (empty string, not None) should trigger search."""
        items = [{"id": 3, "name": "Carrots", "url": "",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            resp = client.get(f"/api/interact/status/{sid}")
            data = resp.get_json()
            assert data["status"] == "search_needed"
        finally:
            _cleanup_session(sid)


# ---------------------------------------------------------------------------
# POST /api/interact/item-complete/<session_id>
# ---------------------------------------------------------------------------

class TestInteractItemComplete:

    def test_unknown_session_returns_404(self, client):
        resp = client.post(
            "/api/interact/item-complete/nonexistent",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_complete_advances_index(self, client, app):
        with app.app_context():
            item = ShoppingItem(name="TestItem", complete=False)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        items = [{"id": item_id, "name": "TestItem", "url": "https://example.com",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            resp = client.post(
                f"/api/interact/item-complete/{sid}",
                data=json.dumps({"product_url": ""}),
                content_type="application/json",
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert data["next_item_index"] == 1
            assert data["session_complete"] is True
        finally:
            _cleanup_session(sid)

    def test_complete_marks_db_item_complete(self, client, app):
        with app.app_context():
            item = ShoppingItem(name="MarkMe", complete=False)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        items = [{"id": item_id, "name": "MarkMe", "url": "",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            client.post(
                f"/api/interact/item-complete/{sid}",
                data=json.dumps({"product_url": ""}),
                content_type="application/json",
            )
            with app.app_context():
                assert ShoppingItem.query.get(item_id).complete is True
        finally:
            _cleanup_session(sid)

    def test_complete_updates_url_when_product_url_provided(self, client, app):
        with app.app_context():
            item = ShoppingItem(name="URLItem", url="", complete=False)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        items = [{"id": item_id, "name": "URLItem", "url": "",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            product_url = "https://shop.example.com/product/123"
            client.post(
                f"/api/interact/item-complete/{sid}",
                data=json.dumps({"product_url": product_url}),
                content_type="application/json",
            )
            with app.app_context():
                assert ShoppingItem.query.get(item_id).url == product_url
        finally:
            _cleanup_session(sid)

    def test_complete_does_not_update_url_for_non_product_page(self, client, app):
        with app.app_context():
            item = ShoppingItem(name="SearchItem", url="https://original.com", complete=False)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        items = [{"id": item_id, "name": "SearchItem", "url": "https://original.com",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            # A search URL (no '/product' in path) should NOT update the stored URL
            client.post(
                f"/api/interact/item-complete/{sid}",
                data=json.dumps({"product_url": "https://shop.example.com/search?q=foo"}),
                content_type="application/json",
            )
            with app.app_context():
                assert ShoppingItem.query.get(item_id).url == "https://original.com"
        finally:
            _cleanup_session(sid)

    def test_complete_when_all_already_processed_returns_400(self, client, app):
        items = [{"id": 999, "name": "X", "url": "",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items, current_index=1)
        try:
            resp = client.post(
                f"/api/interact/item-complete/{sid}",
                data=json.dumps({}),
                content_type="application/json",
            )
            assert resp.status_code == 400
        finally:
            _cleanup_session(sid)

    def test_complete_with_anylist_ids_calls_cross_off(self, client, app):
        from unittest.mock import patch, MagicMock

        with app.app_context():
            item = ShoppingItem(
                name="AnyListCartItem",
                complete=False,
                anylist_item_id="item-cart-1",
                anylist_list_id="list-cart-1",
            )
            db.session.add(item)
            settings = Settings(anylist_email="u@e.com", anylist_password="p")
            db.session.add(settings)
            db.session.commit()
            item_id = item.id

        items = [{"id": item_id, "name": "AnyListCartItem", "url": "",
                  "anylist_item_id": "item-cart-1", "anylist_list_id": "list-cart-1",
                  "complete": False}]
        sid = _make_session(items)
        try:
            mock_client = MagicMock()
            with patch("pyanylist.AnyListClient") as MockCls:
                MockCls.login.return_value = mock_client
                client.post(
                    f"/api/interact/item-complete/{sid}",
                    data=json.dumps({"product_url": ""}),
                    content_type="application/json",
                )
            mock_client.cross_off_item.assert_called_once_with("list-cart-1", "item-cart-1")
        finally:
            _cleanup_session(sid)

    def test_complete_anylist_failure_does_not_fail_request(self, client, app):
        from unittest.mock import patch, MagicMock

        with app.app_context():
            item = ShoppingItem(
                name="AnyListFail",
                complete=False,
                anylist_item_id="item-f",
                anylist_list_id="list-f",
            )
            db.session.add(item)
            settings = Settings(anylist_email="u@e.com", anylist_password="p")
            db.session.add(settings)
            db.session.commit()
            item_id = item.id

        items = [{"id": item_id, "name": "AnyListFail", "url": "",
                  "anylist_item_id": "item-f", "anylist_list_id": "list-f",
                  "complete": False}]
        sid = _make_session(items)
        try:
            mock_client = MagicMock()
            mock_client.cross_off_item.side_effect = Exception("AnyList down")
            with patch("pyanylist.AnyListClient") as MockCls:
                MockCls.login.return_value = mock_client
                resp = client.post(
                    f"/api/interact/item-complete/{sid}",
                    data=json.dumps({"product_url": ""}),
                    content_type="application/json",
                )
            assert resp.status_code == 200
        finally:
            _cleanup_session(sid)


# ---------------------------------------------------------------------------
# POST /api/interact/item-skip/<session_id>
# ---------------------------------------------------------------------------

class TestInteractItemSkip:

    def test_unknown_session_returns_404(self, client):
        resp = client.post("/api/interact/item-skip/nonexistent",
                           data=json.dumps({}), content_type="application/json")
        assert resp.status_code == 404

    def test_skip_advances_index(self, client, app):
        items = [
            {"id": 1, "name": "A", "url": "", "anylist_item_id": None,
             "anylist_list_id": None, "complete": False},
            {"id": 2, "name": "B", "url": "", "anylist_item_id": None,
             "anylist_list_id": None, "complete": False},
        ]
        sid = _make_session(items)
        try:
            resp = client.post(f"/api/interact/item-skip/{sid}",
                               data=json.dumps({}), content_type="application/json")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert data["next_item_index"] == 1
            assert data["session_complete"] is False
        finally:
            _cleanup_session(sid)

    def test_skip_does_not_mark_item_complete(self, client, app):
        with app.app_context():
            item = ShoppingItem(name="SkipMe", complete=False)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        items = [{"id": item_id, "name": "SkipMe", "url": "",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            client.post(f"/api/interact/item-skip/{sid}",
                        data=json.dumps({}), content_type="application/json")
            with app.app_context():
                assert ShoppingItem.query.get(item_id).complete is False
        finally:
            _cleanup_session(sid)

    def test_skip_last_item_marks_session_complete(self, client, app):
        items = [{"id": 1, "name": "Last", "url": "",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            resp = client.post(f"/api/interact/item-skip/{sid}",
                               data=json.dumps({}), content_type="application/json")
            data = resp.get_json()
            assert data["session_complete"] is True
        finally:
            _cleanup_session(sid)

    def test_skip_when_all_already_processed_returns_400(self, client, app):
        items = [{"id": 1, "name": "X", "url": "",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items, current_index=1)
        try:
            resp = client.post(f"/api/interact/item-skip/{sid}",
                               data=json.dumps({}), content_type="application/json")
            assert resp.status_code == 400
        finally:
            _cleanup_session(sid)


# ---------------------------------------------------------------------------
# POST /api/interact/heartbeat/<session_id>
# ---------------------------------------------------------------------------

class TestInteractHeartbeat:

    def test_unknown_session_returns_404(self, client):
        resp = client.post("/api/interact/heartbeat/nonexistent")
        assert resp.status_code == 404

    def test_heartbeat_returns_alive(self, client, app):
        items = [{"id": 1, "name": "X", "url": "",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            resp = client.post(f"/api/interact/heartbeat/{sid}")
            assert resp.status_code == 200
            assert resp.get_json()["status"] == "alive"
        finally:
            _cleanup_session(sid)

    def test_heartbeat_updates_timestamp(self, client, app):
        items = [{"id": 1, "name": "X", "url": "",
                  "anylist_item_id": None, "anylist_list_id": None, "complete": False}]
        sid = _make_session(items)
        try:
            old_hb = InteractSession.query.get(sid).last_heartbeat
            time.sleep(0.01)
            client.post(f"/api/interact/heartbeat/{sid}")
            assert InteractSession.query.get(sid).last_heartbeat >= old_hb
        finally:
            _cleanup_session(sid)

    def test_expired_session_returns_404(self, client):
        resp = client.post("/api/interact/heartbeat/expired-session-id")
        assert resp.status_code == 404
        assert resp.get_json()["status"] == "session_expired"


# ---------------------------------------------------------------------------
# POST /api/add-to-cart
# ---------------------------------------------------------------------------

class TestAddToCart:

    def test_no_incomplete_items_returns_400(self, client, app):
        with app.app_context():
            db.session.add(ShoppingItem(name="Done", complete=True))
            db.session.commit()
        resp = client.post("/api/add-to-cart",
                           data=json.dumps({}), content_type="application/json")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_empty_db_returns_400(self, client):
        resp = client.post("/api/add-to-cart",
                           data=json.dumps({}), content_type="application/json")
        assert resp.status_code == 400

    def test_creates_session_with_incomplete_items(self, client, app, sample_items):
        resp = client.post("/api/add-to-cart",
                           data=json.dumps({}), content_type="application/json")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "session_id" in data
        assert data["total_items"] == 2  # Apples + Bananas are incomplete
        assert "interact_url" in data
        assert data["session_id"] in data["interact_url"]

        # Cleanup
        sid = data["session_id"]
        _cleanup_session(sid)

    def test_session_stored_in_database(self, client, app, sample_items):
        resp = client.post("/api/add-to-cart",
                           data=json.dumps({}), content_type="application/json")
        sid = resp.get_json()["session_id"]
        try:
            sess = InteractSession.query.get(sid)
            assert sess is not None
            assert sess.current_index == 0
            assert sess.state == "running"
        finally:
            _cleanup_session(sid)

    def test_interact_url_format(self, client, app, sample_items):
        resp = client.post("/api/add-to-cart",
                           data=json.dumps({}), content_type="application/json")
        data = resp.get_json()
        sid = data["session_id"]
        try:
            assert data["interact_url"] == f"/interact?session_id={sid}"
        finally:
            _cleanup_session(sid)

    def test_only_incomplete_items_in_session(self, client, app, sample_items):
        """Complete items (Carrots, Dates) must not appear in the session."""
        resp = client.post("/api/add-to-cart",
                           data=json.dumps({}), content_type="application/json")
        sid = resp.get_json()["session_id"]
        try:
            sess = InteractSession.query.get(sid)
            names = [i["name"] for i in sess.items]
            assert "Carrots" not in names
            assert "Dates" not in names
            assert "Apples" in names
            assert "Bananas" in names
        finally:
            _cleanup_session(sid)
