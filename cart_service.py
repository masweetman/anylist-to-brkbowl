"""
Cart service for adding items to shopping carts using Playwright
"""
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time
import json
import os


class CartService:
    """Service to add items to a shopping cart using Playwright"""
    
    def __init__(self, cart_url: str = "https://shop.heinzcatering.berkeleybowl.com/"):
        """
        Initialize the cart service
        
        Args:
            cart_url: Base URL of the shopping cart (default: Berkeley Bowl Heinz Catering)
        """
        self.cart_url = cart_url
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.skip_requested = False
    
    def _inject_skip_bar(self, item_name: str):
        """Inject a skip button into the current page"""
        self.skip_requested = False
        self.page.evaluate("""
            (itemName) => {
                // Remove any existing skip bar
                const existing = document.getElementById('automation-skip-bar');
                if (existing) existing.remove();
                
                // Create skip bar
                const bar = document.createElement('div');
                bar.id = 'automation-skip-bar';
                bar.style.cssText = `
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    background: #FF9800;
                    color: white;
                    padding: 15px 20px;
                    box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.2);
                    z-index: 9999;
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 20px;
                `;
                
                const text = document.createElement('span');
                text.style.cssText = 'font-weight: 500; flex: 1;';
                text.textContent = 'Processing: ' + itemName;
                
                const button = document.createElement('button');
                button.textContent = 'Skip Item';
                button.id = 'automation-skip-btn';
                button.style.cssText = `
                    background: white;
                    color: #FF9800;
                    border: none;
                    padding: 8px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 600;
                    font-size: 14px;
                    transition: all 0.2s ease;
                `;
                
                button.onmouseover = () => {
                    button.style.background = '#fff3e0';
                };
                button.onmouseout = () => {
                    button.style.background = 'white';
                };
                
                button.onclick = () => {
                    // Signal that skip was requested
                    window.__skipRequested = true;
                };
                
                bar.appendChild(text);
                bar.appendChild(button);
                document.body.appendChild(bar);
            }
        """, item_name)
    
    def _remove_skip_bar(self):
        """Remove the skip bar from the page"""
        try:
            self.page.evaluate("""
                () => {
                    const bar = document.getElementById('automation-skip-bar');
                    if (bar) bar.remove();
                    window.__skipRequested = false;
                }
            """)
        except:
            pass
    
    def _check_skip_requested(self) -> bool:
        """Check if the user clicked the skip button"""
        try:
            return self.page.evaluate("() => window.__skipRequested || false")
        except:
            return False
    
    def _start_browser(self):
        """Start Playwright browser with stealth mode using macOS Google Chrome"""
        self.playwright = sync_playwright().start()
        # Use system-installed Google Chrome browser
        try:
            self.browser = self.playwright.chromium.launch(
                headless=False,
                executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            )
        except Exception as e:
            print(f"Failed to launch Chrome: {e}")
            # Fallback to system Chrome
            self.browser = self.playwright.chromium.launch(headless=False, channel="chrome")
        
        # Create context with permissions configured to avoid location prompts
        self.context = self.browser.new_context(
            permissions=['geolocation'],  # Grant permission
            geolocation={'latitude': 37.8044, 'longitude': -122.2712},  # Berkeley, CA coordinates
            ignore_https_errors=True
        )
        # Deny geolocation instead by using an empty permissions list if you want to deny
        # For now, we're granting it with Berkeley coordinates since the shop is in Berkeley
        
        # Apply stealth mode
        stealth = Stealth()
        stealth.apply_stealth_sync(self.context)
        
        # Inject cookies from cookies.json
        self._inject_cookies()
        
        self.page = self.context.new_page()
    
    def _accept_cookies(self):
        """Auto-accept cookies on the current page"""
        try:
            # Specific selectors for Berkeley Bowl and common accept buttons
            accept_selectors = [
                # Berkeley Bowl specific
                'button.cx-accept',
                'button[data-action="accept"]',
                # Generic
                'button:has-text("Accept All")',
                'button:has-text("Accept")',
                'button:has-text("I Accept")',
                'button:has-text("Accept Cookies")',
                'button[class*="accept"]',
                'button[class*="cookie"]',
                '.cookie-accept',
                '#cookie-accept',
                '[data-testid="cookie-consent-accept"]',
            ]
            
            for selector in accept_selectors:
                try:
                    button = self.page.locator(selector).first
                    if button.count() > 0:
                        button.click()
                        print(f"   ✅ Clicked cookie accept button with selector: {selector}")
                        time.sleep(1)  # Wait longer for the action to take effect
                        return True
                except:
                    continue
            
            # If no button found, try using JavaScript
            self.page.evaluate("""
                () => {
                    // Try to find and click accept buttons
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const acceptBtn = buttons.find(btn => 
                        btn.textContent.toLowerCase().includes('accept') &&
                        (btn.textContent.toLowerCase().includes('cookie') || 
                         btn.textContent.toLowerCase().includes('all') ||
                         btn.classList.contains('cx-accept'))
                    );
                    if (acceptBtn) {
                        acceptBtn.click();
                        return true;
                    }
                    return false;
                }
            """)
            
        except Exception as e:
            print(f"   ℹ️  Could not auto-accept cookies: {e}")
    
    def _inject_cookies(self):
        """Load and inject cookies from cookies.json into the browser context"""
        try:
            # Find cookies.json and cookies_prefs.json in the same directory as this file
            cookies_file = os.path.join(os.path.dirname(__file__), 'cookies.json')
            prefs_file = os.path.join(os.path.dirname(__file__), 'cookies_prefs.json')
            
            # Try to load cookies from cookies.json
            cookies_data = []
            if os.path.exists(cookies_file):
                with open(cookies_file, 'r') as f:
                    cookies_data = json.load(f)
            
            # Also load acceptance preference from cookies_prefs.json
            if os.path.exists(prefs_file):
                try:
                    with open(prefs_file, 'r') as f:
                        prefs_data = json.load(f)
                    # Merge acceptance preference cookies into cookies_data
                    if prefs_data and isinstance(prefs_data, list):
                        cookies_data.extend(prefs_data)
                except:
                    pass
            
            if not cookies_data:
                print("ℹ️  No cookies to inject (empty cookies.json)")
                return
            
            if not cookies_data:
                print("ℹ️  No cookies to inject (empty cookies.json)")
                return
            
            # Transform and validate cookies for Playwright compatibility
            valid_cookies = []
            for cookie in cookies_data:
                try:
                    # Create a new cookie dict with only Playwright-compatible fields
                    pw_cookie = {
                        'name': cookie.get('name'),
                        'value': cookie.get('value'),
                        'domain': cookie.get('domain'),
                    }
                    
                    # Add optional fields if present
                    if 'path' in cookie:
                        pw_cookie['path'] = cookie['path']
                    
                    # Convert sameSite to valid Playwright value
                    same_site = cookie.get('sameSite', 'Lax')
                    if same_site == 'no_restriction':
                        same_site = 'None'
                    elif same_site not in ['Strict', 'Lax', 'None']:
                        same_site = 'Lax'
                    pw_cookie['sameSite'] = same_site
                    
                    # Add boolean fields if present
                    if 'secure' in cookie:
                        pw_cookie['secure'] = cookie['secure']
                    if 'httpOnly' in cookie:
                        pw_cookie['httpOnly'] = cookie['httpOnly']
                    
                    # Add expiration date if present (convert to int if needed)
                    if 'expirationDate' in cookie:
                        pw_cookie['expires'] = int(cookie['expirationDate'])
                    
                    valid_cookies.append(pw_cookie)
                    
                except Exception as e:
                    print(f"⚠️  Skipping invalid cookie '{cookie.get('name', 'unknown')}': {e}")
                    continue
            
            if valid_cookies:
                # Inject cookies into the context
                self.context.add_cookies(valid_cookies)
                print(f"✅ Injected {len(valid_cookies)} cookies from cookies.json")
            else:
                print("⚠️  No valid cookies found to inject")
            
        except json.JSONDecodeError as e:
            print(f"⚠️  Invalid JSON in cookies.json: {e}")
        except Exception as e:
            print(f"⚠️  Error loading cookies: {e}")
    

    
    def _get_cart_count(self) -> int:
        """Get the current product count from the cart button title"""
        try:
            # Find the cart button - look for any button with a title containing "Cart"
            cart_buttons = self.page.locator('button[title*="Cart"]')
            
            if cart_buttons.count() > 0:
                # Get the title attribute of the first cart button
                title = cart_buttons.first.get_attribute('title')
                if title:
                    # Extract number from "Cart. Product count in cart 5"
                    import re
                    match = re.search(r'(\d+)', title)
                    if match:
                        return int(match.group(1))
            return 0
        except Exception as e:
            print(f"      ⚠️  Could not read cart count: {e}")
            return 0
    
    def _wait_for_cart_increment(self, initial_count: int, timeout_seconds: int = 30):
        """
        Wait for the cart count to increase from the initial count or skip to be requested
        
        Returns:
            True - cart count incremented
            False - timeout reached
            "skipped" - user clicked skip button
        """
        import re
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            # Check if skip was requested
            if self._check_skip_requested():
                return "skipped"
            
            try:
                current_count = self._get_cart_count()
                if current_count != initial_count:
                    return True
                time.sleep(0.5)  # Poll every 500ms
            except:
                pass
        
        return False
    
    def _wait_for_product_page_navigation(self, timeout_seconds: int = 120) -> str:
        """
        Show popup asking user to click ProductTitle to navigate to product page.
        Wait for the page URL to change to a product page.
        Return the product page URL.
        """
        try:
            # Create and inject a popup
            self.page.evaluate("""
                () => {
                    // Remove any existing popup
                    const existing = document.getElementById('product-nav-popup');
                    if (existing) existing.remove();
                    
                    // Create popup
                    const popup = document.createElement('div');
                    popup.id = 'product-nav-popup';
                    popup.style.cssText = `
                        position: fixed;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        background: #fff;
                        border: 3px solid #4CAF50;
                        border-radius: 8px;
                        padding: 30px;
                        z-index: 10000;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        font-family: Arial, sans-serif;
                        text-align: center;
                        min-width: 400px;
                    `;
                    
                    // Create close button
                    const closeBtn = document.createElement('button');
                    closeBtn.textContent = '✕';
                    closeBtn.style.cssText = `
                        position: absolute;
                        top: 10px;
                        right: 10px;
                        background: #f0f0f0;
                        border: 1px solid #ddd;
                        border-radius: 50%;
                        width: 30px;
                        height: 30px;
                        font-size: 20px;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        transition: all 0.3s ease;
                    `;
                    closeBtn.onmouseover = () => {
                        closeBtn.style.background = '#e0e0e0';
                        closeBtn.style.borderColor = '#999';
                    };
                    closeBtn.onmouseout = () => {
                        closeBtn.style.background = '#f0f0f0';
                        closeBtn.style.borderColor = '#ddd';
                    };
                    closeBtn.onclick = () => {
                        popup.remove();
                    };
                    
                    const title = document.createElement('h2');
                    title.style.color = '#333';
                    title.style.marginBottom = '15px';
                    title.textContent = '📍 Click the Product Title';
                    
                    const message = document.createElement('p');
                    message.style.color = '#666';
                    message.style.fontSize = '16px';
                    message.style.marginBottom = '20px';
                    message.textContent = 'Please click on the product title to navigate to the product page.';
                    
                    const waiting = document.createElement('p');
                    waiting.style.color = '#999';
                    waiting.style.fontSize = '14px';
                    waiting.textContent = 'Waiting for navigation...';
                    
                    popup.appendChild(closeBtn);
                    popup.appendChild(title);
                    popup.appendChild(message);
                    popup.appendChild(waiting);
                    document.body.appendChild(popup);
                }
            """)
            
            print(f"      📢 Popup shown: 'Click the product title to navigate'")
            
            # Wait for URL to change to a product page
            initial_url = self.page.url
            start_time = time.time()
            
            while time.time() - start_time < timeout_seconds:
                current_url = self.page.url
                
                # Check if we've navigated to a product page
                if current_url != initial_url and '/product/' in current_url:
                    # Remove the popup
                    self.page.evaluate("() => { const p = document.getElementById('product-nav-popup'); if (p) p.remove(); }")
                    
                    print(f"      ✅ User navigated to product page: {current_url}")
                    time.sleep(2)  # Wait for page to fully load
                    return current_url
                
                time.sleep(0.5)  # Poll every 500ms
            
            # Timeout - remove popup
            self.page.evaluate("() => { const p = document.getElementById('product-nav-popup'); if (p) p.remove(); }")
            print(f"      ⏱️  Timeout waiting for user to click product title (120 seconds)")
            return ""
            
        except Exception as e:
            print(f"      ⚠️  Error waiting for navigation: {e}")
            try:
                self.page.evaluate("() => { const p = document.getElementById('product-nav-popup'); if (p) p.remove(); }")
            except:
                pass
            return ""
    
    def _confirm_add_to_cart_popup(self, timeout_seconds: int = 120) -> bool:
        """
        Show a popup asking user if they want to add the product to cart.
        Returns True if user clicks "Yes", False if user clicks "No" or timeout.
        """
        try:
            # Create and inject a confirmation popup
            result = self.page.evaluate("""
                () => new Promise((resolve) => {
                    // Remove any existing popup
                    const existing = document.getElementById('confirm-add-to-cart-popup');
                    if (existing) existing.remove();
                    
                    // Create popup
                    const popup = document.createElement('div');
                    popup.id = 'confirm-add-to-cart-popup';
                    popup.style.cssText = `
                        position: fixed;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        background: #fff;
                        border: 3px solid #2196F3;
                        border-radius: 8px;
                        padding: 30px;
                        z-index: 10001;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        font-family: Arial, sans-serif;
                        text-align: center;
                        min-width: 400px;
                    `;
                    
                    const title = document.createElement('h2');
                    title.style.color = '#333';
                    title.style.marginBottom = '20px';
                    title.textContent = '🛒 Add to Cart?';
                    
                    const message = document.createElement('p');
                    message.style.color = '#666';
                    message.style.fontSize = '16px';
                    message.style.marginBottom = '30px';
                    message.textContent = 'Would you like to add this product to your cart?';
                    
                    // Button container
                    const buttonContainer = document.createElement('div');
                    buttonContainer.style.cssText = `
                        display: flex;
                        gap: 15px;
                        justify-content: center;
                    `;
                    
                    // Yes button
                    const yesBtn = document.createElement('button');
                    yesBtn.textContent = 'Yes';
                    yesBtn.style.cssText = `
                        background: #4CAF50;
                        color: white;
                        border: none;
                        padding: 12px 30px;
                        border-radius: 5px;
                        cursor: pointer;
                        font-size: 16px;
                        transition: all 0.3s ease;
                    `;
                    yesBtn.onmouseover = () => { yesBtn.style.background = '#45a049'; };
                    yesBtn.onmouseout = () => { yesBtn.style.background = '#4CAF50'; };
                    yesBtn.onclick = () => {
                        popup.remove();
                        resolve(true);
                    };
                    
                    // No button
                    const noBtn = document.createElement('button');
                    noBtn.textContent = 'No';
                    noBtn.style.cssText = `
                        background: #f44336;
                        color: white;
                        border: none;
                        padding: 12px 30px;
                        border-radius: 5px;
                        cursor: pointer;
                        font-size: 16px;
                        transition: all 0.3s ease;
                    `;
                    noBtn.onmouseover = () => { noBtn.style.background = '#da190b'; };
                    noBtn.onmouseout = () => { noBtn.style.background = '#f44336'; };
                    noBtn.onclick = () => {
                        popup.remove();
                        resolve(false);
                    };
                    
                    buttonContainer.appendChild(yesBtn);
                    buttonContainer.appendChild(noBtn);
                    
                    popup.appendChild(title);
                    popup.appendChild(message);
                    popup.appendChild(buttonContainer);
                    document.body.appendChild(popup);
                })
            """)
            
            # result will be True if user clicked Yes, False if clicked No
            if result:
                print(f"      ✅ User wants to add to cart")
            else:
                print(f"      ❌ User declined to add to cart")
            
            return result
            
        except Exception as e:
            print(f"      ⚠️  Error showing confirmation popup: {e}")
            return False
    
    def _save_cookies(self):
        """Save current browser cookies, separating acceptance preference from main cookies"""
        try:
            if not self.context:
                return
            
            cookies = self.context.cookies()
            
            # Transform to JSON-serializable format
            all_cookies_data = []
            prefs_cookies_data = []
            
            for cookie in cookies:
                cookie_dict = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie['path'],
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False),
                    'sameSite': cookie.get('sameSite', 'Lax'),
                }
                # Convert expires timestamp to integer if present
                if 'expires' in cookie:
                    cookie_dict['expires'] = int(cookie['expires']) if cookie['expires'] else None
                
                # Separate acceptance preference cookies
                if 'consent' in cookie['name'].lower() or 'accept' in cookie['name'].lower():
                    prefs_cookies_data.append(cookie_dict)
                else:
                    all_cookies_data.append(cookie_dict)
            
            # Save main cookies to cookies.json
            import json
            cookies_file = os.path.join(os.path.dirname(__file__), 'cookies.json')
            with open(cookies_file, 'w') as f:
                json.dump(all_cookies_data, f, indent=2)
            
            # Save acceptance preference to separate file
            prefs_file = os.path.join(os.path.dirname(__file__), 'cookies_prefs.json')
            with open(prefs_file, 'w') as f:
                json.dump(prefs_cookies_data, f, indent=2)
            
            print(f"   ✅ Saved {len(all_cookies_data)} cookies to cookies.json")
            if prefs_cookies_data:
                print(f"   ✅ Saved {len(prefs_cookies_data)} acceptance cookies to cookies_prefs.json")
        except Exception as e:
            print(f"   ℹ️  Could not save cookies: {e}")
    
    def _close_browser(self):
        """Close the browser"""
        try:
            # Save cookies before closing
            self._save_cookies()
            
            if self.page:
                try:
                    self.page.close()
                except:
                    pass
            if self.context:
                try:
                    self.context.close()
                except:
                    pass
            if self.browser:
                try:
                    self.browser.close()
                except:
                    pass
            if self.playwright:
                try:
                    self.playwright.stop()
                except:
                    pass
        except:
            pass
    
    def add_items_to_berkeley_bowl(self, items: list) -> dict:
        """
        Add items to Berkeley Bowl Heinz Catering cart
        
        Args:
            items: List of item dictionaries with 'name' and optional 'url' keys
            
        Returns:
            Dictionary with status and results
        """
        try:
            self._start_browser()
            
            results = {
                'success': True,
                'added': [],
                'failed': [],
                'total': len(items)
            }
            
            for item in items:
                item_name = item['name']
                item_url = item.get('url', '').strip()
                
                # Check if user requested to skip this item
                if self._check_skip_requested():
                    print(f"\n⏭️  Skipping item: {item_name}")
                    self._remove_skip_bar()
                    continue
                
                try:
                    if item_url:
                        # Item has a URL - navigate directly to it
                        print(f"\n📍 Processing item: {item_name}")
                        print(f"   Navigating to: {item_url}")
                        self.page.goto(item_url, wait_until="domcontentloaded")
                        time.sleep(2)
                        # Auto-accept cookies
                        self._accept_cookies()
                        
                        # Inject skip bar AFTER page finishes loading
                        self._inject_skip_bar(item_name)
                        
                        # Wait for the product page to fully load by checking for "Add to cart" button (max 3 seconds)
                        print(f"   ⏳ Waiting for product page to load...")
                        max_wait = time.time() + 3  # Max 3 seconds to wait for button
                        button_found = False
                        while time.time() < max_wait:
                            add_to_cart_btn = self.page.locator('button[title="Add to cart"]')
                            if add_to_cart_btn.count() > 0:
                                print(f"   ✅ Product page loaded - 'Add to cart' button is visible")
                                button_found = True
                                break
                            time.sleep(0.5)
                        
                        if button_found:
                            # Get initial cart count
                            initial_count = self._get_cart_count()
                            print(f"   🛒 Initial cart count: {initial_count}")
                            
                            # Wait for user to click "Add to cart" and cart count to increment
                            print(f"   ⏳ Waiting for user to click 'Add to cart'...")
                            wait_result = self._wait_for_cart_increment(initial_count, timeout_seconds=300)  # 5 min timeout for user
                            
                            if wait_result == "skipped":
                                print(f"   ⏭️  Skipping item (skip button clicked)")
                            elif wait_result is True:
                                final_count = self._get_cart_count()
                                print(f"   ✅ Successfully added to cart! Cart count: {initial_count} → {final_count}")
                                # Capture the current page URL (the product page)
                                product_url = self.page.url
                                # Only save if URL contains /product/
                                if '/product/' in product_url:
                                    results['added'].append({'name': item_name, 'url': product_url})
                                else:
                                    print(f"   ⚠️  URL does not contain /product/, skipping save: {product_url}")
                            else:
                                print(f"   ⏱️  Timeout waiting for user to click 'Add to cart' (300 seconds)")
                                results['failed'].append({'item': item_name, 'error': 'Timeout waiting for user to click Add to cart'})
                        else:
                            print(f"   ❌ Add to Cart button not found after waiting 3 seconds")
                            results['failed'].append({'item': item_name, 'error': 'Add to Cart button not found'})
                    else:
                        # No URL - search for the item
                        print(f"\n🔍 Processing item (search mode): {item_name}")
                        print(f"   Navigating to base URL...") 
                        self.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
                        time.sleep(2)
                        # Auto-accept cookies
                        self._accept_cookies()
                        
                        # Inject skip bar AFTER page finishes loading and cookies accepted
                        self._inject_skip_bar(item_name)
                        
                        # Find search input - try multiple selectors
                        search_box = None
                        selectors = [
                            'input[placeholder="Search product"]',
                            'input[type="text"]',
                            'input.search',
                        ]
                        
                        for selector in selectors:
                            try:
                                if self.page.locator(selector).count() > 0:
                                    search_box = self.page.locator(selector).first
                                    print(f"   ✅ Found search box with selector: {selector}")
                                    break
                            except:
                                continue
                        
                        if search_box:
                            print(f"   🔎 Searching for: {item_name}")
                            # Triple-click to select all and clear the field
                            search_box.click(click_count=3)
                            time.sleep(0.3)
                            # Type the search term with proper delay
                            search_box.type(item_name, delay=80)
                            time.sleep(0.5)
                            # Press Enter to search
                            search_box.press("Enter")
                            # Wait for search results to load
                            time.sleep(2)
                            
                            # Get initial cart count
                            initial_count = self._get_cart_count()
                            print(f"   🛒 Initial cart count: {initial_count}")
                            
                            # Wait for user to click "Add to cart" anywhere
                            print(f"   ⏳ Waiting for user to click 'Add to cart'...")
                            wait_result = self._wait_for_cart_increment(initial_count, timeout_seconds=300)  # 5 min timeout
                            
                            if wait_result == "skipped":
                                print(f"   ⏭️  Skipping item (skip button clicked)")
                            elif wait_result is True:
                                final_count = self._get_cart_count()
                                print(f"   ✅ Cart count changed: {initial_count} → {final_count}")
                                
                                # Capture the current URL (product page)
                                product_url = self.page.url
                                print(f"   🔗 Captured product URL: {product_url}")
                                
                                # Only save if URL contains /product/
                                if '/product/' in product_url:
                                    results['added'].append({'name': item_name, 'url': product_url})
                                else:
                                    print(f"   ⚠️  URL does not contain /product/, skipping save: {product_url}")
                            else:
                                print(f"   ⏱️  Timeout waiting for user to click 'Add to cart' (300 seconds)")
                                results['failed'].append({'item': item_name, 'error': 'Timeout waiting for user to click Add to cart'})
                        else:
                            print(f"   ❌ Search box not found with any selector")
                            results['failed'].append({'item': item_name, 'error': 'Search box not found'})
                    
                except Exception as e:
                    error_str = str(e)
                    print(f"   ❌ Error: {error_str}")
                    results['failed'].append({'item': item_name, 'error': error_str})
                finally:
                    # Remove skip bar when done processing this item
                    self._remove_skip_bar()
            
            return results
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'added': [],
                'failed': [item['name'] for item in items]
            }
        finally:
            self._close_browser()
    
    def add_items(self, items: list) -> dict:
        """
        Add items to cart (routes to appropriate service based on cart_url)
        
        Args:
            items: List of item dictionaries with 'name' and optional 'url' keys
            
        Returns:
            Dictionary with results
        """
        if "berkeleybowl" in self.cart_url.lower():
            return self.add_items_to_berkeley_bowl(items)
        else:
            return {
                'success': False,
                'error': f'Cart service not configured for {self.cart_url}'
            }
