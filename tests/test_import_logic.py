#!/usr/bin/env python
"""Test the import logic with case-insensitive matching"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from app import app, db, ShoppingItem

print("🧪 Testing import logic...")
print("=" * 50)

with app.app_context():
    # Start fresh
    print("\n1️⃣  Setting up test data...")
    ShoppingItem.query.delete()
    db.session.commit()
    
    # Add some initial items
    items = [
        ShoppingItem(name="Milk", complete=False, url=""),
        ShoppingItem(name="Bread", complete=False, url=""),
        ShoppingItem(name="Eggs", complete=False, url=""),
    ]
    for item in items:
        db.session.add(item)
    db.session.commit()
    
    initial_items = ShoppingItem.query.all()
    print(f"   Created {len(initial_items)} initial items:")
    for item in initial_items:
        print(f"      - {item.name} (complete={item.complete})")
    
    # Simulate import with case variations and duplicates
    print("\n2️⃣  Simulating import process...")
    
    # First, mark all as complete
    print("   Marking all items as completed...")
    ShoppingItem.query.update({ShoppingItem.complete: True})
    db.session.commit()
    
    # Import list with case variations and new items
    import_items = ["milk", "BREAD", "Butter", "Cheese"]
    imported_count = 0
    updated_count = 0
    
    print(f"   Processing {len(import_items)} imported items:")
    
    for item_name in import_items:
        # Case-insensitive search
        existing = ShoppingItem.query.filter(
            ShoppingItem.name.ilike(item_name)
        ).first()
        
        if existing:
            existing.complete = False
            updated_count += 1
            print(f"      ↩️  Updated: {existing.name} (matched '{item_name}')")
        else:
            new_item = ShoppingItem(name=item_name, complete=False, url="")
            db.session.add(new_item)
            imported_count += 1
            print(f"      ✨ New: {item_name}")
    
    db.session.commit()
    
    # Show results
    print(f"\n3️⃣  Results:")
    print(f"   New items: {imported_count}")
    print(f"   Updated items: {updated_count}")
    print(f"   Total: {imported_count + updated_count}")
    
    print(f"\n4️⃣  Final state:")
    all_items = ShoppingItem.query.order_by(ShoppingItem.name).all()
    for item in all_items:
        status = "✅ complete" if item.complete else "❌ incomplete"
        print(f"      {item.name:12} {status}")
    
    print("\n✅ Test complete!")
