"""
Unit tests for database models: ShoppingItem and Settings.
Tests cover model creation, field defaults, to_dict(), constraints, and edge cases.
"""
import pytest
from datetime import datetime
from database import db, ShoppingItem, Settings


class TestShoppingItemModel:
    """Unit tests for the ShoppingItem model."""

    def test_create_minimal_item(self, app):
        """ShoppingItem can be created with only a name."""
        with app.app_context():
            item = ShoppingItem(name="Milk")
            db.session.add(item)
            db.session.commit()
            fetched = ShoppingItem.query.filter_by(name="Milk").first()
            assert fetched is not None
            assert fetched.name == "Milk"

    def test_default_complete_is_false(self, app):
        """complete defaults to False."""
        with app.app_context():
            item = ShoppingItem(name="Eggs")
            db.session.add(item)
            db.session.commit()
            fetched = ShoppingItem.query.filter_by(name="Eggs").first()
            assert fetched.complete is False

    def test_default_url_is_none(self, app):
        """url defaults to None when not provided."""
        with app.app_context():
            item = ShoppingItem(name="Bread")
            db.session.add(item)
            db.session.commit()
            fetched = ShoppingItem.query.filter_by(name="Bread").first()
            assert fetched.url is None

    def test_created_at_set_on_insert(self, app):
        """created_at is populated automatically on insert."""
        with app.app_context():
            item = ShoppingItem(name="Butter")
            db.session.add(item)
            db.session.commit()
            fetched = ShoppingItem.query.filter_by(name="Butter").first()
            assert fetched.created_at is not None
            assert isinstance(fetched.created_at, datetime)

    def test_updated_at_set_on_insert(self, app):
        """updated_at is populated automatically on insert."""
        with app.app_context():
            item = ShoppingItem(name="Cheese")
            db.session.add(item)
            db.session.commit()
            fetched = ShoppingItem.query.filter_by(name="Cheese").first()
            assert fetched.updated_at is not None

    def test_name_unique_constraint(self, app):
        """Inserting two items with the same name raises an IntegrityError."""
        from sqlalchemy.exc import IntegrityError
        with app.app_context():
            db.session.add(ShoppingItem(name="Duplicate"))
            db.session.commit()
            db.session.add(ShoppingItem(name="Duplicate"))
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_to_dict_keys(self, app):
        """to_dict() returns all expected keys."""
        with app.app_context():
            item = ShoppingItem(name="Yogurt", url="https://example.com", complete=True)
            db.session.add(item)
            db.session.commit()
            d = item.to_dict()
            assert set(d.keys()) == {
                "id", "name", "complete", "url",
                "anylist_item_id", "anylist_list_id",
                "created_at", "updated_at",
            }

    def test_to_dict_values(self, app):
        """to_dict() returns correct field values."""
        with app.app_context():
            item = ShoppingItem(
                name="Yogurt",
                url="https://example.com",
                complete=True,
                anylist_item_id="aid-1",
                anylist_list_id="lid-1",
            )
            db.session.add(item)
            db.session.commit()
            d = item.to_dict()
            assert d["name"] == "Yogurt"
            assert d["url"] == "https://example.com"
            assert d["complete"] is True
            assert d["anylist_item_id"] == "aid-1"
            assert d["anylist_list_id"] == "lid-1"
            assert isinstance(d["id"], int)

    def test_to_dict_timestamps_are_iso_strings(self, app):
        """to_dict() serialises timestamps as ISO-8601 strings."""
        with app.app_context():
            item = ShoppingItem(name="Tofu")
            db.session.add(item)
            db.session.commit()
            d = item.to_dict()
            # Should not raise
            datetime.fromisoformat(d["created_at"])
            datetime.fromisoformat(d["updated_at"])

    def test_anylist_ids_default_to_none(self, app):
        """anylist_item_id and anylist_list_id default to None."""
        with app.app_context():
            item = ShoppingItem(name="Tempeh")
            db.session.add(item)
            db.session.commit()
            d = item.to_dict()
            assert d["anylist_item_id"] is None
            assert d["anylist_list_id"] is None

    def test_complete_can_be_toggled(self, app):
        """complete field can be updated from False to True and back."""
        with app.app_context():
            item = ShoppingItem(name="Kale", complete=False)
            db.session.add(item)
            db.session.commit()

            item.complete = True
            db.session.commit()
            assert ShoppingItem.query.filter_by(name="Kale").first().complete is True

            item.complete = False
            db.session.commit()
            assert ShoppingItem.query.filter_by(name="Kale").first().complete is False

    def test_name_max_length_255(self, app):
        """Name at exactly 255 characters is accepted."""
        with app.app_context():
            long_name = "A" * 255
            item = ShoppingItem(name=long_name)
            db.session.add(item)
            db.session.commit()
            assert ShoppingItem.query.filter_by(name=long_name).first() is not None

    def test_url_max_length_500(self, app):
        """URL at exactly 500 characters is accepted."""
        with app.app_context():
            long_url = "https://example.com/" + "x" * 480
            item = ShoppingItem(name="LongURL", url=long_url)
            db.session.add(item)
            db.session.commit()
            assert ShoppingItem.query.filter_by(name="LongURL").first().url == long_url


class TestSettingsModel:
    """Unit tests for the Settings model."""

    def test_create_empty_settings(self, app):
        """Settings can be created with no fields set."""
        with app.app_context():
            s = Settings()
            db.session.add(s)
            db.session.commit()
            fetched = Settings.query.first()
            assert fetched is not None

    def test_to_dict_keys(self, app):
        """Settings.to_dict() returns all expected keys."""
        with app.app_context():
            s = Settings()
            db.session.add(s)
            db.session.commit()
            d = s.to_dict()
            assert set(d.keys()) == {
                "id", "anylist_email", "anylist_password",
                "anylist_list_name", "has_password", "updated_at",
            }

    def test_has_password_false_when_no_password(self, app):
        """has_password is False when app_password is None."""
        with app.app_context():
            s = Settings()
            db.session.add(s)
            db.session.commit()
            assert s.to_dict()["has_password"] is False

    def test_has_password_true_when_password_set(self, app):
        """has_password is True when app_password is set."""
        from werkzeug.security import generate_password_hash
        with app.app_context():
            s = Settings(app_password=generate_password_hash("secret"))
            db.session.add(s)
            db.session.commit()
            assert s.to_dict()["has_password"] is True

    def test_password_not_exposed_in_to_dict(self, app):
        """The raw app_password hash is NOT included in to_dict() output."""
        from werkzeug.security import generate_password_hash
        with app.app_context():
            s = Settings(app_password=generate_password_hash("secret"))
            db.session.add(s)
            db.session.commit()
            d = s.to_dict()
            assert "app_password" not in d

    def test_updated_at_set_on_insert(self, app):
        """updated_at is populated on insert."""
        with app.app_context():
            s = Settings(anylist_email="a@b.com")
            db.session.add(s)
            db.session.commit()
            assert s.updated_at is not None

    def test_to_dict_updated_at_is_iso_string(self, app):
        """updated_at in to_dict() is an ISO-8601 string."""
        with app.app_context():
            s = Settings()
            db.session.add(s)
            db.session.commit()
            datetime.fromisoformat(s.to_dict()["updated_at"])

    def test_anylist_fields_stored_and_retrieved(self, app):
        """AnyList credentials and list name are stored and retrieved correctly."""
        with app.app_context():
            s = Settings(
                anylist_email="user@example.com",
                anylist_password="hunter2",
                anylist_list_name="Groceries",
            )
            db.session.add(s)
            db.session.commit()
            fetched = Settings.query.first()
            assert fetched.anylist_email == "user@example.com"
            assert fetched.anylist_password == "hunter2"
            assert fetched.anylist_list_name == "Groceries"
