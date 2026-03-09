#!/usr/bin/env python3
from database import db, ShoppingItem, Settings
from app import app

with app.app_context():
    # Get a test item with an ID
    test_item = ShoppingItem.query.filter_by(name='Bread').first()
    
    # Get settings with credentials
    settings = Settings.query.first()
    
    if test_item and test_item.anylist_item_id:
        print(f"Testing cross_off_item with:")
        print(f"  Item: {test_item.name}")
        print(f"  Item ID: {test_item.anylist_item_id}")
        
        if settings and settings.anylist_email and settings.anylist_password:
            try:
                from pyanylist import AnyListClient
                client = AnyListClient.login(settings.anylist_email, settings.anylist_password)
                
                # Get the list
                lists = client.get_lists()
                print(f"\nFound {len(lists)} list(s)")
                
                if lists:
                    target_list = lists[0]
                    print(f"Using list: {target_list.name} (ID: {target_list.id})")
                    
                    # Inspect cross_off_item signature
                    import inspect
                    sig = inspect.signature(client.cross_off_item)
                    print(f"cross_off_item signature: {sig}")
                    
                    # Try calling with different approaches
                    print("\nAttempt 1: client.cross_off_item(item_id)")
                    try:
                        result = client.cross_off_item(test_item.anylist_item_id)
                        print(f"  Success: {result}")
                    except Exception as e:
                        print(f"  Failed: {e}")
                    
                    print("\nAttempt 2: client.cross_off_item(list_id, item_id)")
                    try:
                        result = client.cross_off_item(target_list.id, test_item.anylist_item_id)
                        print(f"  Success: {result}")
                    except Exception as e:
                        print(f"  Failed: {e}")
                    
                    print("\nAttempt 3: target_list.cross_off_item(item_uid)")
                    try:
                        result = target_list.cross_off_item(test_item.anylist_item_id)
                        print(f"  Success: {result}")
                    except Exception as e:
                        print(f"  Failed: {e}")
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("No AnyList credentials stored")
    else:
        print("No test item found")

