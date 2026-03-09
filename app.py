import os
import json
import csv
from io import StringIO, BytesIO
from flask import Flask, render_template, request, jsonify, send_file
from database import db, ShoppingItem, Settings
from dotenv import load_dotenv
from cart_service import CartService

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shopping_list.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

with app.app_context():
    db.create_all()
    
    # Handle schema migration for existing databases
    # Add anylist_item_id and anylist_list_id columns if they don't exist
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('shopping_items')]
    if 'anylist_item_id' not in columns:
        with db.engine.connect() as conn:
            conn.execute(db.text('ALTER TABLE shopping_items ADD COLUMN anylist_item_id VARCHAR(255)'))
            conn.commit()
        print("✅ Added anylist_item_id column to shopping_items table")
    if 'anylist_list_id' not in columns:
        with db.engine.connect() as conn:
            conn.execute(db.text('ALTER TABLE shopping_items ADD COLUMN anylist_list_id VARCHAR(255)'))
            conn.commit()
        print("✅ Added anylist_list_id column to shopping_items table")


@app.route('/')
def index():
    """Render the main shopping list page"""
    return render_template('index.html')


@app.route('/settings')
def settings():
    """Render the settings page"""
    return render_template('settings.html')


@app.route('/api/items', methods=['GET'])
def get_items():
    """Get all shopping items"""
    items = ShoppingItem.query.order_by(ShoppingItem.complete, ShoppingItem.updated_at.desc()).all()
    return jsonify([item.to_dict() for item in items])


@app.route('/api/items', methods=['POST'])
def add_item():
    """Add a new shopping item"""
    data = request.json
    
    if not data or not data.get('name'):
        return jsonify({'error': 'Item name is required'}), 400
    
    # Check if item already exists
    existing_item = ShoppingItem.query.filter_by(name=data['name']).first()
    if existing_item:
        return jsonify({'error': 'Item already exists'}), 409
    
    item = ShoppingItem(
        name=data['name'],
        url=data.get('url', ''),
        complete=False
    )
    
    db.session.add(item)
    db.session.commit()
    
    return jsonify(item.to_dict()), 201


@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    """Update a shopping item"""
    item = ShoppingItem.query.get_or_404(item_id)
    data = request.json
    
    if 'name' in data:
        # Check if new name already exists (and it's not the same item)
        existing = ShoppingItem.query.filter_by(name=data['name']).first()
        if existing and existing.id != item_id:
            return jsonify({'error': 'Item name already exists'}), 409
        item.name = data['name']
    
    if 'complete' in data:
        item.complete = data['complete']
        
        # If marking as complete and we have AnyList IDs, cross it off in AnyList
        if data['complete'] and item.anylist_item_id and item.anylist_list_id:
            try:
                settings = Settings.query.first()
                if settings and settings.anylist_email and settings.anylist_password:
                    from pyanylist import AnyListClient
                    client = AnyListClient.login(settings.anylist_email, settings.anylist_password)
                    print(f"   📍 Attempting to cross off in AnyList: {item.name}")
                    print(f"      (List ID: {item.anylist_list_id}, Item ID: {item.anylist_item_id})")
                    # Cross off the item in AnyList - requires both list_id and item_id
                    result = client.cross_off_item(item.anylist_list_id, item.anylist_item_id)
                    print(f"   ✅ Crossed off in AnyList: {item.name} (Result: {result})")
                else:
                    print(f"   ℹ️  No AnyList credentials configured, skipping cross-off")
            except Exception as e:
                # Log error but don't fail the request
                print(f"   ⚠️  Could not cross off '{item.name}' in AnyList: {str(e)}")
        elif data['complete'] and not (item.anylist_item_id and item.anylist_list_id):
            print(f"   ℹ️  No AnyList IDs stored for '{item.name}' - item may not have been imported from AnyList")
    
    if 'url' in data:
        item.url = data['url']
    
    db.session.commit()
    
    return jsonify(item.to_dict())


@app.route('/api/import-anylist', methods=['POST'])
def import_anylist():
    """Import items from AnyList"""
    try:
        from pyanylist import AnyListClient
        data = request.json
        
        email = data.get('email')
        password = data.get('password')
        list_name = data.get('list_name', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Initialize AnyListClient with credentials
        client = AnyListClient.login(email, password)
        
        # Find the list to import
        target_list = None
        if list_name:
            target_list = client.get_list_by_name(list_name)
        else:
            # Get all lists and use the first one
            lists = client.get_lists()
            if not lists:
                return jsonify({'error': 'No lists found in AnyList'}), 400
            target_list = lists[0]
        
        if not target_list:
            return jsonify({'error': f'List "{list_name}" not found in AnyList'}), 400
        
        # Mark all existing items as completed before import
        print("📋 Marking all items as completed before import...")
        ShoppingItem.query.update({ShoppingItem.complete: True})
        db.session.commit()
        print("✅ All items marked as completed")
        
        # Get items from the list
        items = target_list.items
        
        imported_count = 0
        updated_count = 0
        
        for item in items:
            item_name = item.name.strip()
            
            # Get the item ID - try different attributes that pyanylist might use
            anylist_id = None
            for attr in ['uid', 'id', 'item_id']:
                if hasattr(item, attr):
                    anylist_id = getattr(item, attr)
                    break
            
            # Case-insensitive search for existing item
            existing = ShoppingItem.query.filter(
                ShoppingItem.name.ilike(item_name)
            ).first()
            
            if existing:
                # Item exists - mark as incomplete
                existing.complete = False
                existing.anylist_item_id = anylist_id
                existing.anylist_list_id = target_list.id
                updated_count += 1
                print(f"   ↩️  Updated existing: {existing.name} (AnyList ID: {anylist_id})")
            else:
                # Create new item
                new_item = ShoppingItem(
                    name=item_name,
                    complete=False,
                    url='',
                    anylist_item_id=anylist_id,
                    anylist_list_id=target_list.id
                )
                db.session.add(new_item)
                imported_count += 1
                print(f"   ✨ New item: {item_name} (AnyList ID: {anylist_id})")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Imported items from {target_list.name}',
            'imported_count': imported_count,
            'updated_count': updated_count,
            'total_processed': imported_count + updated_count
        })
    
    except ImportError:
        return jsonify({'error': 'pyanylist library not installed'}), 500
    except RuntimeError as e:
        # Handle AnyList authentication errors
        error_msg = str(e)
        if 'Invalid credentials' in error_msg or 'Unauthorized' in error_msg:
            return jsonify({'error': 'Invalid AnyList email or password'}), 401
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get user settings"""
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
        db.session.commit()
    return jsonify(settings.to_dict())


@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Save user settings"""
    data = request.json
    
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
    
    if 'anylist_email' in data:
        settings.anylist_email = data['anylist_email']
    
    if 'anylist_password' in data:
        settings.anylist_password = data['anylist_password']
    
    if 'anylist_list_name' in data:
        settings.anylist_list_name = data['anylist_list_name']
    
    db.session.add(settings)
    db.session.commit()
    
    return jsonify(settings.to_dict())


@app.route('/api/cookies', methods=['GET'])
def get_cookies():
    """Get cookies from cookies.json"""
    try:
        cookies_file = os.path.join(os.path.dirname(__file__), 'cookies.json')
        if os.path.exists(cookies_file):
            with open(cookies_file, 'r') as f:
                cookies = f.read()
                return jsonify({'cookies': cookies})
        return jsonify({'cookies': '[]'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cookies', methods=['POST'])
def save_cookies():
    """Save cookies to cookies.json"""
    try:
        data = request.json
        cookies = data.get('cookies', '[]')
        
        # Validate JSON
        import json
        json.loads(cookies)  # This will raise an error if invalid JSON
        
        cookies_file = os.path.join(os.path.dirname(__file__), 'cookies.json')
        with open(cookies_file, 'w') as f:
            f.write(cookies)
        
        return jsonify({'success': True, 'message': 'Cookies saved successfully'})
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/add-to-cart', methods=['POST'])
def add_to_cart():
    """Add all incomplete items to shopping cart using Playwright"""
    try:
        data = request.json
        cart_url = data.get('cart_url', 'https://shop.heinzcatering.berkeleybowl.com/')
        
        # Get all incomplete items
        items = ShoppingItem.query.filter_by(complete=False).all()
        
        if not items:
            return jsonify({'error': 'No incomplete items to add to cart'}), 400
        
        # Create item dictionaries with name and url
        item_data = [{'name': item.name, 'url': item.url} for item in items]
        
        # Initialize cart service and add items
        cart_service = CartService(cart_url)
        results = cart_service.add_items(item_data)
        
        # Update database items with extracted product URLs and mark as complete
        if results.get('success') and results.get('added'):
            # Get AnyList credentials for cross-off
            settings = Settings.query.first()
            anylist_client = None
            if settings and settings.anylist_email and settings.anylist_password:
                try:
                    from pyanylist import AnyListClient
                    anylist_client = AnyListClient.login(settings.anylist_email, settings.anylist_password)
                except Exception as e:
                    print(f"   ⚠️  Could not connect to AnyList: {str(e)}")
            
            for added_item in results['added']:
                item_name = added_item.get('name') if isinstance(added_item, dict) else added_item
                item_url = added_item.get('url') if isinstance(added_item, dict) else ''
                
                # Find and update the item in database
                item = ShoppingItem.query.filter_by(name=item_name).first()
                if item:
                    # Mark item as complete
                    item.complete = True
                    # Update URL if it was extracted
                    if item_url:
                        item.url = item_url
                        print(f"   ✅ Updated {item_name} URL: {item_url}")
                    else:
                        print(f"   ✅ Marked {item_name} as complete")
                    
                    # Cross off in AnyList if we have IDs and client
                    if anylist_client and item.anylist_item_id and item.anylist_list_id:
                        try:
                            anylist_client.cross_off_item(item.anylist_list_id, item.anylist_item_id)
                            print(f"   ✅ Crossed off in AnyList: {item_name}")
                        except Exception as e:
                            print(f"   ⚠️  Could not cross off '{item_name}' in AnyList: {str(e)}")
            
            db.session.commit()
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export-csv', methods=['GET'])
def export_csv():
    """Export all shopping items as CSV"""
    try:
        items = ShoppingItem.query.all()
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Name', 'URL', 'Complete'])
        
        # Write items
        for item in items:
            writer.writerow([item.name, item.url or '', 'Yes' if item.complete else 'No'])
        
        # Create bytes file
        csv_data = output.getvalue()
        bytes_output = BytesIO(csv_data.encode('utf-8'))
        bytes_output.seek(0)
        
        return send_file(
            bytes_output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='shopping_list.csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/import-csv', methods=['POST'])
def import_csv():
    """Import shopping items from CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        # Parse CSV
        stream = StringIO(file.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)
        
        imported_count = 0
        updated_count = 0
        errors = []
        
        for row in reader:
            try:
                item_name = row.get('Name', '').strip()
                if not item_name:
                    continue
                
                item_url = row.get('URL', '').strip()
                is_complete = row.get('Complete', 'No').lower() in ['yes', 'true', '1']
                
                # Check if item exists
                existing = ShoppingItem.query.filter(
                    ShoppingItem.name.ilike(item_name)
                ).first()
                
                if existing:
                    existing.url = item_url
                    existing.complete = is_complete
                    updated_count += 1
                else:
                    new_item = ShoppingItem(
                        name=item_name,
                        url=item_url,
                        complete=is_complete
                    )
                    db.session.add(new_item)
                    imported_count += 1
            except Exception as e:
                errors.append(f'Error processing row {item_name}: {str(e)}')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'updated_count': updated_count,
            'total_processed': imported_count + updated_count,
            'errors': errors
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)
