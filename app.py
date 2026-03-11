import csv
import os
import re
import time
import threading
from io import StringIO, BytesIO
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, Response
from werkzeug.security import generate_password_hash, check_password_hash
import requests as http_requests
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
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')

# ---------------------------------------------------------------------------
# Shop reverse-proxy constants & helpers
# ---------------------------------------------------------------------------
_SHOP_BASE = 'https://shop.heinzcatering.berkeleybowl.com'
_SHOP_COOKIE_PREFIX = '_shopck_'   # shop cookies stored on our domain with this prefix

# Headers we must not forward upstream or downstream
_DROP_REQ_HEADERS  = frozenset(['host', 'content-length', 'transfer-encoding',
                                 'connection', 'accept-encoding', 'cookie'])
# CSP / x-frame-options would block our injected script; drop them
_DROP_RESP_HEADERS = frozenset(['content-encoding', 'transfer-encoding', 'connection',
                                 'content-security-policy', 'x-frame-options',
                                 'strict-transport-security'])


def _rewrite_url(url: str) -> str:
    """Rewrite an absolute shop URL (or root-relative path) to go through /shop-proxy."""
    if url.startswith(_SHOP_BASE):
        suffix = url[len(_SHOP_BASE):]
        return '/shop-proxy' + (suffix if suffix.startswith('/') else '/' + suffix)
    if url.startswith('/') and not url.startswith('//'):
        return '/shop-proxy' + url
    return url


def _rewrite_html(html: str, session_id: str) -> str:
    """Rewrite URLs in HTML and inject the floating control-panel overlay."""

    # 1. Absolute shop URLs in href/src/action attributes
    html = re.sub(
        r'(href|src|action)="(https://shop\.heinzcatering\.berkeleybowl\.com)(/[^"]*|)"',
        lambda m: f'{m.group(1)}="/shop-proxy{m.group(3) or "/"}"',
        html,
    )
    # 2. Root-relative URLs in href/src/action (skip already-rewritten /shop-proxy ones)
    html = re.sub(
        r'(href|src|action)="(/(?!shop-proxy)[^"]*)"',
        lambda m: f'{m.group(1)}="/shop-proxy{m.group(2)}"',
        html,
    )
    # 3. Absolute shop origin appearing in JS strings / fetch calls
    html = html.replace(
        '"' + _SHOP_BASE, '"/shop-proxy'
    ).replace(
        "'" + _SHOP_BASE, "'/shop-proxy"
    )

    # 4. Inject overlay
    overlay = _build_overlay(session_id)
    if '</body>' in html:
        html = html.replace('</body>', overlay + '\n</body>', 1)
    else:
        html += '\n' + overlay
    return html


def _rewrite_text(text: str) -> str:
    """Light URL rewrite for CSS / JS (no overlay injection)."""
    return text.replace(_SHOP_BASE, '/shop-proxy')


def _build_overlay(session_id: str) -> str:
    sid_json = session_id  # safe: session_id is a hex UUID from secrets.token_hex
    return f"""<script id="__bb_overlay">(function(){{
var SID="{sid_json}";
var SHOP_BASE="{_SHOP_BASE}";

function mk(tag,css,html){{var e=document.createElement(tag);if(css)e.style.cssText=css;if(html)e.innerHTML=html;return e;}}
function btn(txt,bg,fn){{var b=mk('button','border:none;padding:9px 14px;border-radius:4px;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap;background:'+bg+';color:white;font-family:inherit;',txt);b.onclick=fn;return b;}}

var panel  = mk('div','position:fixed;top:0;left:0;right:0;z-index:2147483647;background:#3949ab;color:white;padding:10px 14px;display:flex;align-items:center;gap:10px;font-family:Segoe UI,sans-serif;box-shadow:0 2px 6px rgba(0,0,0,.3);');
var info   = mk('div','flex:1;min-width:0;');
var lbl    = mk('div','font-size:10px;opacity:.7;text-transform:uppercase;letter-spacing:.5px;','Shopping for');
var iname  = mk('div','font-size:15px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;','…');
var prog   = mk('div','font-size:12px;opacity:.7;white-space:nowrap;flex-shrink:0;','');
var skipB  = btn('Skip','rgba(255,255,255,.18)',doSkip);
var addB   = btn('✓ Added to Cart','#43a047',doAdded);
var canB   = btn('✕ Cancel','rgba(255,255,255,.12)',doCancel);
info.append(lbl,iname);
panel.append(info,prog,skipB,addB,canB);

function disable(){{skipB.disabled=addB.disabled=true;}}

async function status(){{
  try{{var r=await fetch('/api/interact/status/'+SID);return r.ok?r.json():null;}}
  catch(e){{return null;}}
}}

function toProxy(url){{
  if(!url)return'/shop-proxy/';
  if(url.startsWith(SHOP_BASE))return'/shop-proxy'+url.slice(SHOP_BASE.length);
  if(url.startsWith('/'))return'/shop-proxy'+url;
  return url;
}}

async function goNext(){{
  var s=await status();
  if(!s||s.status==='complete'){{window.location.href='/';return;}}
  var url=s.url||(SHOP_BASE+'/search?filter%5Betext%5D='+btoa(unescape(encodeURIComponent(s.search_query)))+'&filter%5Bwidget%5D=1');
  window.location.href=toProxy(url);
}}

async function doSkip(){{
  disable();
  await fetch('/api/interact/item-skip/'+SID,{{method:'POST'}}).catch(function(){{}});
  goNext();
}}

async function doAdded(){{
  disable();
  var s=await status();
  if(!s)return;
  var productUrl=location.href;
  var can=document.querySelector('link[rel="canonical"]');
  if(can&&can.href)productUrl=can.href;
  await fetch('/api/interact/item-complete/'+SID,{{
    method:'POST',headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{item_id:s.item.id,product_url:productUrl,cart_count_changed:true}})
  }}).catch(function(){{}});
  goNext();
}}

function doCancel(){{window.location.href='/';}}

setInterval(function(){{fetch('/api/interact/heartbeat/'+SID,{{method:'POST'}}).catch(function(){{}});}},5000);

async function init(){{
  var s=await status();
  if(!s)return;
  if(s.status==='complete'){{window.location.href='/';return;}}
  iname.textContent=s.item.name;
  prog.textContent=s.item_number+' / '+s.total_items;
  document.body.style.marginTop='0';
  document.body.style.paddingTop='60px';
  document.body.prepend(panel);
}}

if(document.readyState==='loading'){{document.addEventListener('DOMContentLoaded',init);}}
else{{init();}}
}})();
</script>"""


@app.route('/shop-proxy/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@app.route('/shop-proxy/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def shop_proxy(path):
    """Reverse-proxy the Berkeley Bowl shop and inject the cart overlay."""
    # Read or persist the shopping session id via cookie
    session_id = request.args.get('_sid') or request.cookies.get('interact_session_id', '')

    # Pass the raw query string through unchanged, just strip our _sid param.
    # Rebuilding via request.args re-encodes bracket-style keys and breaks the shop.
    raw_qs = request.query_string.decode('utf-8', errors='replace')
    clean_qs = '&'.join(p for p in raw_qs.split('&') if p and not p.startswith('_sid='))
    target = _SHOP_BASE + '/' + path + ('?' + clean_qs if clean_qs else '')

    fwd_headers = {k: v for k, v in request.headers
                   if k.lower() not in _DROP_REQ_HEADERS}
    fwd_headers['Host'] = 'shop.heinzcatering.berkeleybowl.com'
    # Ensure a real browser User-Agent so the shop doesn't 403 us
    if 'User-Agent' not in fwd_headers or 'python' in fwd_headers.get('User-Agent', '').lower():
        fwd_headers['User-Agent'] = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                                     'AppleWebKit/537.36 (KHTML, like Gecko) '
                                     'Chrome/120.0.0.0 Safari/537.36')

    # Extract shop cookies stored on our domain (strip our prefix)
    shop_cookies = {
        k[len(_SHOP_COOKIE_PREFIX):]: v
        for k, v in request.cookies.items()
        if k.startswith(_SHOP_COOKIE_PREFIX)
    }

    try:
        upstream = http_requests.request(
            method=request.method,
            url=target,
            headers=fwd_headers,
            data=request.get_data(),
            cookies=shop_cookies,
            allow_redirects=False,
            timeout=20,
        )
    except http_requests.exceptions.RequestException as exc:
        return jsonify({'error': f'Proxy error: {exc}'}), 502

    ct = upstream.headers.get('Content-Type', '')

    if 'text/html' in ct:
        body = _rewrite_html(upstream.text, session_id)
        resp = Response(body, status=upstream.status_code, content_type=ct)
    elif any(t in ct for t in ('text/css', 'javascript', 'text/plain', 'application/json')):
        body = _rewrite_text(upstream.text)
        resp = Response(body, status=upstream.status_code, content_type=ct)
    else:
        resp = Response(upstream.content, status=upstream.status_code, content_type=ct)

    # Forward safe response headers
    for h, v in upstream.headers.items():
        if h.lower() not in _DROP_RESP_HEADERS:
            resp.headers[h] = v

    # Rewrite redirect Location header
    if upstream.status_code in (301, 302, 303, 307, 308):
        loc = upstream.headers.get('Location', '')
        resp.headers['Location'] = _rewrite_url(loc)

    # Store shop cookies on our domain (prefixed, first-party)
    for cookie in upstream.cookies:
        resp.set_cookie(
            _SHOP_COOKIE_PREFIX + cookie.name,
            cookie.value,
            max_age=cookie._rest.get('Max-Age'),
            httponly=bool(cookie._rest.get('HttpOnly')),
            samesite='Lax',
        )

    # Persist the session_id across proxy navigations
    if session_id:
        resp.set_cookie('interact_session_id', session_id, httponly=True, samesite='Lax')

    return resp


@app.before_request
def require_login():
    if request.endpoint in ('login', 'logout', 'reset_app', 'static', 'shop_proxy'):
        return
    settings = Settings.query.first()
    if not (settings and settings.app_password):
        return  # no password set — allow all access

    # The /interact page and its API endpoints are authenticated by the
    # session_id token in the URL/request rather than the login cookie.
    # This is necessary because iOS browsers (Safari and Chrome) do not
    # reliably share session cookies with new tabs opened via window.open(),
    # so the new tab would otherwise always get a 401.
    if request.endpoint == 'interact':
        return
    if request.endpoint in (
        'interact_status',
        'interact_item_complete',
        'interact_item_skip',
        'interact_heartbeat',
    ):
        return

    if not session.get('authenticated'):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Authentication required'}), 401
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        settings = Settings.query.first()
        if settings and settings.app_password and check_password_hash(settings.app_password, password):
            session['authenticated'] = True
            return redirect(url_for('index'))
        error = 'Incorrect password.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

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

    settings_columns = [col['name'] for col in inspector.get_columns('settings')]
    if 'app_password' not in settings_columns:
        with db.engine.connect() as conn:
            conn.execute(db.text('ALTER TABLE settings ADD COLUMN app_password VARCHAR(255)'))
            conn.commit()


@app.route('/')
def index():
    """Render the main shopping list page"""
    settings = Settings.query.first()
    has_password = bool(settings and settings.app_password)
    return render_template('index.html', has_password=has_password)


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


@app.route('/api/reset', methods=['POST'])
def reset_app():
    """Forgot-password reset: deletes all shopping items, clears AnyList
    credentials and the app password.  Accessible without authentication so
    that a locked-out user can recover access."""
    try:
        ShoppingItem.query.delete()

        settings = Settings.query.first()
        if settings:
            settings.anylist_email = None
            settings.anylist_password = None
            settings.anylist_list_name = None
            settings.app_password = None

        db.session.commit()
        session.clear()

        return jsonify({'success': True, 'message': 'App has been reset'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/password', methods=['POST'])
def set_app_password():
    """Set or clear the app login password"""
    data = request.json
    new_password = data.get('password', '').strip()

    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)

    settings.app_password = generate_password_hash(new_password) if new_password else None
    db.session.commit()

    # If password was cleared, drop the current session so the page stays accessible
    if not new_password:
        session.clear()

    return jsonify({'success': True, 'has_password': bool(new_password)})


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
