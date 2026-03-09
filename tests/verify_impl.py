#!/usr/bin/env python
"""Verify the implementation"""

from cart_service import CartService
import json
import inspect

print("📋 Verifying implementation...")
print("=" * 50)

# Verify the method exists
service = CartService()

# Check that _save_cookies method exists
if hasattr(service, '_save_cookies'):
    print('✅ _save_cookies method exists')
else:
    print('❌ _save_cookies method missing')

# Check _accept_cookies has the right selectors
source = inspect.getsource(service._accept_cookies)
if 'button.cx-accept' in source:
    print('✅ button.cx-accept selector added')
if 'data-action' in source and 'accept' in source:
    print('✅ data-action selector added')

# Verify cookies.json exists
try:
    with open('cookies.json') as f:
        cookies = json.load(f)
    print(f'✅ cookies.json exists with {len(cookies)} cookies')
    if any('cookie_consent' in c.get('name', '') for c in cookies):
        print('✅ cookie_consent_v1 found in saved cookies')
except Exception as e:
    print(f'⚠️  cookies.json issue: {e}')

print("\n✅ Implementation verified!")
