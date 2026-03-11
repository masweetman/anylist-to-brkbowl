"""Berkeley Bowl shop scraper.

Uses Playwright (headless Chromium) to intercept the shop SPA's internal
API calls and return structured product data.  This lets the iOS interact
view render search results natively instead of bouncing the user to a
separate browser tab for every item.

Usage (from Flask):
    from scraper import search
    results = search("organic apples")   # returns list of product dicts

Each product dict has the shape:
    {
        "name":        str,
        "price":       str,   # may be empty
        "image_url":   str,   # may be empty
        "product_url": str,   # canonical shop URL, may be empty
    }

Requirements:
    pip install playwright
    playwright install chromium
"""

import base64
import time
from typing import Optional

_SHOP_ORIGIN = "https://shop.heinzcatering.berkeleybowl.com"

# Simple in-process cache: {query_lower → (timestamp, results)}
_CACHE: dict = {}
_CACHE_TTL = 300  # seconds


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search(query: str, force: bool = False) -> list:
    """Search Berkeley Bowl's shop for *query* and return product dicts.

    Results are cached for _CACHE_TTL seconds.  Pass force=True to bypass.
    Raises RuntimeError when playwright is not installed.
    """
    key = query.lower().strip()
    if not force and key in _CACHE:
        ts, results = _CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            return results

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        raise RuntimeError(
            "playwright is not installed. "
            "Run: pip install playwright && playwright install chromium"
        )

    captured: list = []  # Response objects collected during page load

    def _on_response(response):
        """Collect JSON responses from the shop domain for later parsing."""
        try:
            ct = response.headers.get("content-type", "")
            if "json" not in ct:
                return
            if "heinzcatering" not in response.url:
                return
            captured.append(response)
        except Exception:
            pass

    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        page.on("response", _on_response)

        try:
            page.goto(_search_url(query), wait_until="networkidle", timeout=25_000)
        except PWTimeout:
            pass  # Partial load is fine – use whatever responses we captured

        # First try: extract products from intercepted JSON API responses
        for resp in captured:
            try:
                data = resp.json()
                products = _extract_products_from_data(resp.url, data)
                if products:
                    results = products
                    break
            except Exception:
                continue

        # Second try: fall back to DOM scraping
        if not results:
            results = _scrape_dom(page)

        ctx.close()
        browser.close()

    _CACHE[key] = (time.time(), results)
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _search_url(query: str) -> str:
    encoded = base64.b64encode(query.encode("utf-8")).decode("ascii")
    return f"{_SHOP_ORIGIN}/search?filter[etext]={encoded}&filter[widget]=1"


def _extract_products_from_data(url: str, data) -> list:
    """Pull a product list out of a JSON response blob.

    Returns [] if the response doesn't look like product data.
    """
    candidates: list = []

    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict):
        for key in ("products", "items", "results", "data", "hits"):
            if key in data and isinstance(data[key], list):
                candidates = data[key]
                break
        if not candidates:
            nested = data.get("data")
            if isinstance(nested, dict):
                for key in ("products", "items", "results"):
                    if key in nested and isinstance(nested[key], list):
                        candidates = nested[key]
                        break

    out = []
    for item in candidates[:20]:
        if not isinstance(item, dict):
            continue
        p = _normalise_product(item)
        if p:
            out.append(p)
    return out


def _normalise_product(item: dict) -> Optional[dict]:
    """Map arbitrary product dict fields to our standard shape."""
    name = (
        item.get("name") or item.get("title") or item.get("product_name") or ""
    ).strip()
    if not name:
        return None

    price_raw = (
        item.get("price")
        or item.get("regular_price")
        or item.get("sale_price")
        or item.get("unit_price")
        or ""
    )
    price = str(price_raw).strip() if price_raw else ""

    image = (
        item.get("image")
        or item.get("image_url")
        or item.get("thumbnail")
        or item.get("photo")
        or ""
    )
    if isinstance(image, dict):
        image = image.get("url") or image.get("src") or ""
    image = str(image).strip() if image else ""
    # Only keep absolute URLs to avoid leaking relative paths
    if image and not image.startswith("http"):
        image = ""

    slug_or_url = str(
        item.get("slug") or item.get("url") or item.get("path") or ""
    ).strip()
    product_id = str(item.get("id") or item.get("product_id") or "").strip()

    product_url = ""
    if slug_or_url.startswith("http"):
        product_url = slug_or_url
    elif slug_or_url.startswith("/"):
        product_url = f"{_SHOP_ORIGIN}{slug_or_url}"
    elif slug_or_url:
        product_url = f"{_SHOP_ORIGIN}/product/{slug_or_url}"
    elif product_id:
        product_url = f"{_SHOP_ORIGIN}/product/{product_id}"

    return {
        "name": name,
        "price": price,
        "image_url": image,
        "product_url": product_url,
    }


def _scrape_dom(page) -> list:
    """Best-effort DOM scraping when API interception yields nothing."""
    results = []
    selectors = [
        ".product-card",
        ".product-item",
        ".product",
        "[data-product]",
        ".item-card",
        ".catalog-item",
    ]
    for sel in selectors:
        try:
            els = page.locator(sel)
            count = els.count()
            if count == 0:
                continue
            for i in range(min(count, 15)):
                el = els.nth(i)
                try:
                    name = (
                        el.locator(".product-name,.name,h2,h3")
                        .first.text_content(timeout=2000) or ""
                    ).strip()
                    if not name:
                        continue

                    price = ""
                    try:
                        price = (
                            el.locator(".price,.product-price")
                            .first.text_content(timeout=1000) or ""
                        ).strip()
                    except Exception:
                        pass

                    image_url = ""
                    try:
                        src = el.locator("img").first.get_attribute("src", timeout=1000) or ""
                        if src.startswith("http"):
                            image_url = src
                    except Exception:
                        pass

                    product_url = ""
                    try:
                        href = el.locator("a").first.get_attribute("href", timeout=1000) or ""
                        if href.startswith("/"):
                            product_url = f"{_SHOP_ORIGIN}{href}"
                        elif href.startswith("http"):
                            product_url = href
                    except Exception:
                        pass

                    results.append({
                        "name": name,
                        "price": price,
                        "image_url": image_url,
                        "product_url": product_url,
                    })
                except Exception:
                    continue
            if results:
                break
        except Exception:
            continue
    return results
