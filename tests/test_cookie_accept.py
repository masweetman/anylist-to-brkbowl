#!/usr/bin/env python
"""Test cookie acceptance in action"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🧪 Testing automatic cookie acceptance...")
print("=" * 50)

try:
    service = CartService()
    service._start_browser()
    print("✅ Browser started")
    
    # Navigate and test cookie acceptance
    print("\n📍 Navigating to Berkeley Bowl multiple times...")
    
    for i in range(2):
        print(f"\n   Attempt {i+1}:")
        service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
        print(f"   ✅ Page loaded")
        time.sleep(2)  # Give page time to load cookie banner
        
        # Inspect page for cookie-related content
        try:
            buttons = service.page.locator("button").all()
            print(f"   📊 Total buttons on page: {len(buttons)}")
            
            # Check for any button with 'accept' or 'cookie' in text or classes
            button_info = service.page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('button');
                    const info = [];
                    buttons.forEach((btn, idx) => {
                        const text = btn.textContent.trim();
                        const classes = btn.className;
                        if (text.toLowerCase().includes('accept') || 
                            classes.toLowerCase().includes('accept') ||
                            classes.toLowerCase().includes('cookie')) {
                            info.push({
                                index: idx,
                                text: text.substring(0, 50),
                                classes: classes,
                                dataAction: btn.getAttribute('data-action'),
                                dataTestid: btn.getAttribute('data-testid')
                            });
                        }
                    });
                    return info;
                }
            """)
            
            if button_info:
                print(f"   🎯 Found {len(button_info)} accept-related buttons:")
                for btn in button_info:
                    print(f"         - Text: '{btn['text']}', Classes: '{btn['classes']}', data-action: {btn['dataAction']}")
            else:
                print(f"   ℹ️  No accept-related buttons found on page")
                
        except Exception as e:
            print(f"   ⚠️  Error inspecting page: {e}")
        
        # Try to accept cookies
        print(f"   📞 Calling _accept_cookies()...")
        service._accept_cookies()
        time.sleep(1)
    
    service._close_browser()
    print("\n✅ Test complete - Cookies should have been automatically accepted!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
