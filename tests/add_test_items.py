#!/usr/bin/env python
"""Add test items to the database"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from app import app, db, ShoppingItem

with app.app_context():
    # Clear existing items
    ShoppingItem.query.delete()
    db.session.commit()
    print("✅ Cleared existing items")
    
    # Add test items
    test_items = [
        ShoppingItem(name="Milk", url="", complete=False),
        ShoppingItem(name="Bread", url="", complete=False),
        ShoppingItem(name="Eggs", url="", complete=False),
    ]
    
    for item in test_items:
        db.session.add(item)
    
    db.session.commit()
    print(f"✅ Added {len(test_items)} test items")
    
    # Verify items were added
    all_items = ShoppingItem.query.all()
    print(f"\n📋 Total items in database: {len(all_items)}")
    for item in all_items:
        print(f"   - {item.name} (URL: {item.url or 'None'})")
