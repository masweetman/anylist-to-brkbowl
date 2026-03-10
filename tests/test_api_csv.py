"""
Integration tests for CSV import/export endpoints:
  GET  /api/export-csv
  POST /api/import-csv
"""
import io
import json
import pytest
from database import db, ShoppingItem


class TestExportCsv:
    """GET /api/export-csv"""

    def test_export_returns_200(self, client):
        resp = client.get("/api/export-csv")
        assert resp.status_code == 200

    def test_export_content_type_is_csv(self, client):
        resp = client.get("/api/export-csv")
        assert "text/csv" in resp.content_type

    def test_export_has_header_row(self, client):
        resp = client.get("/api/export-csv")
        text = resp.data.decode("utf-8")
        assert text.startswith("Name,URL,Complete")

    def test_export_empty_db_has_only_header(self, client):
        resp = client.get("/api/export-csv")
        lines = [l for l in resp.data.decode("utf-8").splitlines() if l.strip()]
        assert len(lines) == 1  # header only

    def test_export_includes_all_items(self, client, sample_items):
        resp = client.get("/api/export-csv")
        text = resp.data.decode("utf-8")
        assert "Apples" in text
        assert "Bananas" in text
        assert "Carrots" in text
        assert "Dates" in text

    def test_export_complete_column_yes_no(self, client, app):
        with app.app_context():
            db.session.add(ShoppingItem(name="Done", complete=True))
            db.session.add(ShoppingItem(name="Todo", complete=False))
            db.session.commit()
        resp = client.get("/api/export-csv")
        text = resp.data.decode("utf-8")
        # Verify each item's row has the correct Complete value
        lines = text.splitlines()
        done_line = next(l for l in lines if "Done" in l)
        todo_line = next(l for l in lines if "Todo" in l)
        assert done_line.endswith(",Yes")
        assert todo_line.endswith(",No")

    def test_export_attachment_header(self, client):
        resp = client.get("/api/export-csv")
        cd = resp.headers.get("Content-Disposition", "")
        assert "attachment" in cd
        assert "shopping_list.csv" in cd

    def test_export_url_included(self, client, sample_item):
        resp = client.get("/api/export-csv")
        text = resp.data.decode("utf-8")
        # The URL must appear on the same row as the item name
        lines = text.splitlines()
        apples_line = next(l for l in lines if "Apples" in l)
        assert "https://example.com/apples" in apples_line

    def test_export_item_with_no_url_has_empty_url_field(self, client, app):
        with app.app_context():
            db.session.add(ShoppingItem(name="NoURL", url="", complete=False))
            db.session.commit()
        resp = client.get("/api/export-csv")
        text = resp.data.decode("utf-8")
        assert "NoURL" in text


class TestImportCsv:
    """POST /api/import-csv"""

    def _make_csv_file(self, content: str, filename: str = "test.csv"):
        return (io.BytesIO(content.encode("utf-8")), filename)

    def test_import_new_items(self, client, app):
        csv_content = "Name,URL,Complete\nMilk,https://example.com/milk,No\nEggs,,No\n"
        data = {"file": self._make_csv_file(csv_content)}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        result = resp.get_json()
        assert result["success"] is True
        assert result["imported_count"] == 2
        assert result["updated_count"] == 0

    def test_import_updates_existing_items(self, client, sample_item, app):
        csv_content = "Name,URL,Complete\nApples,https://new.example.com/apples,Yes\n"
        data = {"file": self._make_csv_file(csv_content)}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        result = resp.get_json()
        assert result["updated_count"] == 1
        assert result["imported_count"] == 0

    def test_import_updates_complete_status(self, client, sample_item, app):
        csv_content = "Name,URL,Complete\nApples,,Yes\n"
        data = {"file": self._make_csv_file(csv_content)}
        client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        with app.app_context():
            item = ShoppingItem.query.filter_by(name="Apples").first()
            assert item.complete is True

    def test_import_complete_true_values(self, client, app):
        """'yes', 'true', '1' all map to complete=True."""
        # Use index-prefixed names to avoid SQLite case-insensitive UNIQUE collisions
        # (e.g. 'Item_yes' and 'Item_Yes' would collide)
        true_values = ["yes", "Yes", "YES", "true", "True", "1"]
        for idx, val in enumerate(true_values):
            item_name = f"TrueItem{idx}"
            csv_content = f"Name,URL,Complete\n{item_name},,{val}\n"
            data = {"file": self._make_csv_file(csv_content)}
            client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        with app.app_context():
            for idx, val in enumerate(true_values):
                item_name = f"TrueItem{idx}"
                item = ShoppingItem.query.filter_by(name=item_name).first()
                assert item is not None, f"Item '{item_name}' not found (value='{val}')"
                assert item.complete is True, f"Expected complete=True for value '{val}'"

    def test_import_complete_false_values(self, client, app):
        """'no', 'false', '0' all map to complete=False."""
        # Use index-prefixed names to avoid SQLite case-insensitive UNIQUE collisions
        false_values = ["no", "No", "false", "False", "0"]
        for idx, val in enumerate(false_values):
            item_name = f"FalseItem{idx}"
            csv_content = f"Name,URL,Complete\n{item_name},,{val}\n"
            data = {"file": self._make_csv_file(csv_content)}
            client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        with app.app_context():
            for idx, val in enumerate(false_values):
                item_name = f"FalseItem{idx}"
                item = ShoppingItem.query.filter_by(name=item_name).first()
                assert item is not None, f"Item '{item_name}' not found (value='{val}')"
                assert item.complete is False, f"Expected complete=False for value '{val}'"

    def test_import_no_file_returns_400(self, client):
        resp = client.post("/api/import-csv", data={}, content_type="multipart/form-data")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_import_empty_filename_returns_400(self, client):
        data = {"file": (io.BytesIO(b""), "")}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_import_non_csv_file_returns_400(self, client):
        data = {"file": (io.BytesIO(b"not a csv"), "data.txt")}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400
        assert "CSV" in resp.get_json()["error"]

    def test_import_skips_rows_with_empty_name(self, client, app):
        csv_content = "Name,URL,Complete\n,https://example.com,No\nMilk,,No\n"
        data = {"file": self._make_csv_file(csv_content)}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        result = resp.get_json()
        # Only "Milk" should be imported; empty-name row is skipped
        assert result["imported_count"] == 1

    def test_import_case_insensitive_match(self, client, app):
        """Existing item 'Apples' should be updated when CSV has 'apples'."""
        with app.app_context():
            db.session.add(ShoppingItem(name="Apples", complete=False))
            db.session.commit()
        csv_content = "Name,URL,Complete\napples,,Yes\n"
        data = {"file": self._make_csv_file(csv_content)}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        result = resp.get_json()
        assert result["updated_count"] == 1
        assert result["imported_count"] == 0

    def test_import_returns_total_processed(self, client, app):
        csv_content = "Name,URL,Complete\nA,,No\nB,,No\nC,,No\n"
        data = {"file": self._make_csv_file(csv_content)}
        resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        result = resp.get_json()
        assert result["total_processed"] == 3

    def test_import_persists_to_db(self, client, app):
        csv_content = "Name,URL,Complete\nPersistMe,https://example.com,No\n"
        data = {"file": self._make_csv_file(csv_content)}
        client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        with app.app_context():
            item = ShoppingItem.query.filter_by(name="PersistMe").first()
            assert item is not None
            assert item.url == "https://example.com"

    def test_roundtrip_export_then_import(self, client, app):
        """Export items to CSV, clear DB, re-import, verify items restored."""
        with app.app_context():
            db.session.add(ShoppingItem(name="RoundTrip1", url="https://rt1.com", complete=False))
            db.session.add(ShoppingItem(name="RoundTrip2", url="", complete=True))
            db.session.commit()

        # Export
        export_resp = client.get("/api/export-csv")
        csv_bytes = export_resp.data

        # Clear DB
        with app.app_context():
            ShoppingItem.query.delete()
            db.session.commit()

        # Re-import
        data = {"file": (io.BytesIO(csv_bytes), "shopping_list.csv")}
        import_resp = client.post("/api/import-csv", data=data, content_type="multipart/form-data")
        assert import_resp.status_code == 200
        result = import_resp.get_json()
        assert result["imported_count"] == 2

        with app.app_context():
            assert ShoppingItem.query.filter_by(name="RoundTrip1").first() is not None
            assert ShoppingItem.query.filter_by(name="RoundTrip2").first() is not None
