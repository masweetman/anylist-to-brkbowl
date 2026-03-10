from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ShoppingItem(db.Model):
    """Database model for shopping list items"""
    __tablename__ = 'shopping_items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    complete = db.Column(db.Boolean, default=False)
    url = db.Column(db.String(500), nullable=True)
    anylist_item_id = db.Column(db.String(255), nullable=True)
    anylist_list_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'complete': self.complete,
            'url': self.url,
            'anylist_item_id': self.anylist_item_id,
            'anylist_list_id': self.anylist_list_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Settings(db.Model):
    """Database model for user settings"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    anylist_email = db.Column(db.String(255), nullable=True)
    anylist_password = db.Column(db.String(255), nullable=True)
    anylist_list_name = db.Column(db.String(255), nullable=True)
    app_password = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'anylist_email': self.anylist_email,
            'anylist_password': self.anylist_password,
            'anylist_list_name': self.anylist_list_name,
            'has_password': bool(self.app_password),
            'updated_at': self.updated_at.isoformat()
        }
