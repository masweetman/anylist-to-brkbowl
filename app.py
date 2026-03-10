import csv
import time
import threading
from io import StringIO, BytesIO
from flask import Flask, render_template, request, jsonify, send_file
from database import db, ShoppingItem, Settings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global state for interactive add-to-cart sessions
# Maps session_id -> {items: [...], current_index: 0, state: 'idle'|'running'|'complete', last_heartbeat: time}
_sessions = {}
_sessions_lock = threading.Lock()

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


@app.route('/interact')
def interact():
    """Render the interactive shopping page (opened in new tab)"""
    return render_template('interact.html')


@app.route('/api/items', methods=['GET'])
def get_items():
    """Get all shopping items"""
    items = ShoppingItem.query.order_by(ShoppingItem.complete, ShoppingItem.updated_at.desc()).all()
    return jsonify([item.to_dict() for item in items])


@app.route('/api/interact/status/<session_id>', methods=['GET'])
def interact_status(session_id):
    """Get current session status and instructions for next item"""
    try:
        with _sessions_lock:
            if session_id not in _sessions:
                return jsonify({'error': 'Session not found'}), 404
            
            session = _sessions[session_id]
            session['last_heartbeat'] = time.time()  # Update heartbeat
            
            # Check if session is done
            if session['current_index'] >= len(session['items']):
                return jsonify({
                    'status': 'complete',
                    'message': 'All items processed'
                })
            
            # Get current item
            current_item = session['items'][session['current_index']]
            
            # If item has URL, return it directly
            if current_item['url']:
                return jsonify({
                    'status': 'ready',
                    'item': current_item,
                    'item_number': session['current_index'] + 1,
                    'total_items': len(session['items']),
                    'action': 'navigate',
                    'url': current_item['url']
                })
            else:
                # Need to search - generate search URL for user
                return jsonify({
                    'status': 'search_needed',
                    'item': current_item,
                    'item_number': session['current_index'] + 1,
                    'total_items': len(session['items']),
                    'action': 'search',
                    'search_query': current_item['name']
                })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/interact/item-complete/<session_id>', methods=['POST'])
def interact_item_complete(session_id):
    """Mark current item as complete and move to next"""
    try:
        data = request.json
        cart_count_changed = data.get('cart_count_changed', False)
        product_url = data.get('product_url', '')
        
        with _sessions_lock:
            if session_id not in _sessions:
                return jsonify({'error': 'Session not found'}), 404
            
            session = _sessions[session_id]
            
            if session['current_index'] >= len(session['items']):
                return jsonify({'error': 'All items already processed'}), 400
            
            # Mark item as complete
            current_item = session['items'][session['current_index']]
            current_item['complete'] = True
            
            # Update database
            db_item = ShoppingItem.query.get(current_item['id'])
            if db_item:
                db_item.complete = True
                
                # Update URL only if it's a product page (not a search page)
                if product_url and '/product' in product_url:
                    db_item.url = product_url
                
                # Cross off in AnyList if possible
                if db_item.anylist_item_id and db_item.anylist_list_id:
                    try:
                        settings = Settings.query.first()
                        if settings and settings.anylist_email and settings.anylist_password:
                            from pyanylist import AnyListClient
                            client = AnyListClient.login(settings.anylist_email, settings.anylist_password)
                            client.cross_off_item(db_item.anylist_list_id, db_item.anylist_item_id)
                            print(f"   ✅ Crossed off in AnyList: {db_item.name}")
                    except Exception as e:
                        print(f"   ⚠️  Could not cross off in AnyList: {str(e)}")
                
                db.session.commit()
            
            # Move to next item
            session['current_index'] += 1
            
            return jsonify({
                'success': True,
                'next_item_index': session['current_index'],
                'total_items': len(session['items']),
                'session_complete': session['current_index'] >= len(session['items'])
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/interact/item-skip/<session_id>', methods=['POST'])
def interact_item_skip(session_id):
    """Skip current item (do not mark complete) and move to next"""
    try:
        with _sessions_lock:
            if session_id not in _sessions:
                return jsonify({'error': 'Session not found'}), 404

            session = _sessions[session_id]

            if session['current_index'] >= len(session['items']):
                return jsonify({'error': 'All items already processed'}), 400

            # Advance without marking complete
            session['current_index'] += 1

            return jsonify({
                'success': True,
                'next_item_index': session['current_index'],
                'total_items': len(session['items']),
                'session_complete': session['current_index'] >= len(session['items'])
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/interact/heartbeat/<session_id>', methods=['POST'])
def interact_heartbeat(session_id):
    """Keep session alive - called periodically by client"""
    try:
        with _sessions_lock:
            if session_id not in _sessions:
                return jsonify({'status': 'session_expired'}), 404
            
            session = _sessions[session_id]
            session['last_heartbeat'] = time.time()
            
            return jsonify({'status': 'alive'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
        
        # Sync completion state with AnyList if we have IDs
        if item.anylist_item_id and item.anylist_list_id:
            try:
                settings = Settings.query.first()
                if settings and settings.anylist_email and settings.anylist_password:
                    from pyanylist import AnyListClient
                    client = AnyListClient.login(settings.anylist_email, settings.anylist_password)
                    if data['complete']:
                        client.cross_off_item(item.anylist_list_id, item.anylist_item_id)
                        print(f"   ✅ Crossed off in AnyList: {item.name}")
                    else:
                        client.uncheck_item(item.anylist_list_id, item.anylist_item_id)
                        print(f"   ↩️  Unchecked in AnyList: {item.name}")
            except Exception as e:
                # Log error but don't fail the request
                print(f"   ⚠️  Could not sync '{item.name}' with AnyList: {str(e)}")
    
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


@app.route('/api/add-to-cart', methods=['POST'])
def add_to_cart():
    """Start interactive add-to-cart session and open in new tab"""
    try:
        import uuid
        
        # Get all incomplete items
        items = ShoppingItem.query.filter_by(complete=False).all()
        
        if not items:
            return jsonify({'error': 'No incomplete items to add to cart'}), 400
        
        # Create session
        session_id = str(uuid.uuid4())
        item_list = [
            {
                'id': item.id,
                'name': item.name,
                'url': item.url,
                'anylist_item_id': item.anylist_item_id,
                'anylist_list_id': item.anylist_list_id,
                'complete': False
            }
            for item in items
        ]
        
        with _sessions_lock:
            _sessions[session_id] = {
                'items': item_list,
                'current_index': 0,
                'state': 'running',
                'last_heartbeat': time.time()
            }
        
        return jsonify({
            'session_id': session_id,
            'total_items': len(item_list),
            'interact_url': f'/interact?session_id={session_id}'
        })
    
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
