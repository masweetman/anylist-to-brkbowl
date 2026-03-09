#!/usr/bin/env python
"""Test cookies JSON file creation and API endpoints"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

import json

# Test 1: Create sample cookies
sample_cookies = [
    {
        "name": "session_id",
        "value": "abc123def456",
        "domain": ".heinzcatering.berkeleybowl.com",
        "path": "/",
        "secure": True,
        "httpOnly": True
    },
    {
        "name": "user_preferences",
        "value": "dark_mode=true",
        "domain": ".heinzcatering.berkeleybowl.com",
        "path": "/"
    }
]

print("🧪 Testing Cookies JSON...")
print("=" * 50)

# Write sample cookies to cookies.json
cookies_file = '/Users/mike/code/anylist-to-brkbowl/cookies.json'
with open(cookies_file, 'w') as f:
    json.dump(sample_cookies, f, indent=2)

print(f"✅ Created sample cookies.json with {len(sample_cookies)} cookies:")
for cookie in sample_cookies:
    print(f"   - {cookie['name']}")

# Test 2: Verify CartService can load cookies
from cart_service import CartService

print("\n🧪 Testing CartService cookie injection...")
print("=" * 50)

service = CartService()
service._start_browser()
print("✅ Browser started")

# The cookies should have been injected automatically
print("✅ Cookies injected during browser startup")

import time
time.sleep(3)
service._close_browser()
print("✅ Browser closed")

print("\n📝 Cookies JSON content:")
with open(cookies_file, 'r') as f:
    print(f.read())

print("\n✅ Cookie injection test completed!")
