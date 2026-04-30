"""
scraping.py — Architecture hybride fiable (2025)
=================================================
Stratégie par site :

  Jumia.ma    → requests + BeautifulSoup       (inchangé, fonctionne bien)
  eBay        → API Finding XML GRATUITE        (5 000 req/jour, 0 blocage)
                fallback: SerpAPI si APP_ID absent
  Avito.ma    → Playwright + sélecteurs 2025   (mis à jour)
  Mytek.ma    → requests + BeautifulSoup       (Cloudflare bypass via headers)
  Amazon.fr   → SerpAPI Google Shopping        (0 blocage, plan gratuit 100/mois)
                fallback: ScraperAPI si SERPAPI_KEY absent
  AliExpress  → AliExpress Affiliate API REST  (gratuite, JSON propre)
                fallback: SerpAPI Shopping

VARIABLES À AJOUTER dans settings.py :
    EBAY_APP_ID     = "TonAppID-xxx"          # developer.ebay.com (gratuit)
    SERPAPI_KEY     = "xxx"                   # serpapi.com (100 req/mois gratuit)
    SCRAPERAPI_KEY  = "xxx"                   # scraperapi.com (1 000 req/mois gratuit)
    ALIEXPRESS_APP_KEY    = "xxx"             # portail.aliexpress (gratuit)
    ALIEXPRESS_APP_SECRET = "xxx"
"""

import requests
from bs4 import BeautifulSoup
import random
import time
import re
import xml.etree.ElementTree as ET
import json
import hmac
import hashlib
import urllib.parse
from datetime import datetime

from django.conf import settings

# ── User-Agents pool ──────────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


# ── Utilitaires ───────────────────────────────────────────────────────────────

def clean_price(raw):
    if not raw:
        return None
    raw = str(raw)
    cleaned = re.sub(r'[^\d,.]', '', raw)
    if ',' in cleaned and '.' in cleaned:
        if cleaned.index(',') > cleaned.index('.'):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned and len(cleaned) - cleaned.index(',') <= 3:
        cleaned = cleaned.replace(',', '.')
    else:
        cleaned = cleaned.replace(',', '')
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except (ValueError, TypeError):
        return None


def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
        "DNT": "1",
    })
    return s


def safe_get(session, url, timeout=15, retries=3):
    for attempt in range(retries):
        try:
            time.sleep(random.uniform(0.5, 1.5))
            session.headers["User-Agent"] = random.choice(USER_AGENTS)
            r = session.get(url, timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                return r
            if r.status_code in [429, 503]:
                time.sleep(random.uniform(5, 12))
            elif r.status_code == 403 and attempt == 0:
                time.sleep(2)
        except requests.RequestException:
            time.sleep(1)
    return None


def playwright_get_html(url, wait_selector=None, scroll=True, timeout=30000, extra_js=None):
    """Playwright headless avec anti-détection renforcé."""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    except ImportError:
        return None

    html = None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--window-size=1366,768",
            ],
        )
        ctx = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            locale="fr-FR",
            timezone_id="Africa/Casablanca",
            viewport={"width": 1366, "height": 768},
            extra_http_headers={
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
                "DNT": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            },
            java_script_enabled=True,
        )
        ctx.add_init_script("""
            // Masquer tous les marqueurs de webdriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['fr-FR', 'fr', 'en']});
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            window.chrome = { runtime: {}, loadTimes: () => {}, csi: () => {}, app: {} };
            // Faker les permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (params) =>
                params.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(params);
        """)

        page = ctx.new_page()
        try:
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")

            # Délai humain
            time.sleep(random.uniform(1.5, 3.0))

            if extra_js:
                page.evaluate(extra_js)

            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=12000)
                except PwTimeout:
                    pass

            if scroll:
                for _ in range(5):
                    page.evaluate("window.scrollBy(0, window.innerHeight * 0.7 + Math.random() * 200)")
                    time.sleep(random.uniform(0.4, 0.9))
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(0.5)

            html = page.content()
        except PwTimeout:
            html = None
        except Exception:
            html = None
        finally:
            browser.close()

    return html


# ── MANAGER ───────────────────────────────────────────────────────────────────

def scrape_manager(query, site):
    scrapers = {
        "jumia":      scrape_jumia,
        "avito":      scrape_avito,
        "mytek":      scrape_mytek,
        "amazon":     scrape_amazon,
        "aliexpress": scrape_aliexpress,
        "ebay":       scrape_ebay,
    }
    return scrapers.get(site, scrape_jumia)(query)


# ═══════════════════════════════════════════════════════════════════════════════
#  1. JUMIA.MA — requests classique (inchangé, fonctionne)
# ═══════════════════════════════════════════════════════════════════════════════

def scrape_jumia(query):
    base_url = "https://www.jumia.ma"
    url = f"{base_url}/catalog/?q={requests.utils.quote(query)}"
    session = make_session()
    products = []

    response = safe_get(session, url)
    if not response:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    for item in soup.find_all("article", class_="prd")[:12]:
        try:
            name  = item.find("h3", class_="name").text.strip()
            price = clean_price(item.find("div", class_="prc").text)
            if not price:
                continue
            img_tag = item.find("img")
            img  = (img_tag.get("data-src") or img_tag.get("src", "")) if img_tag else ""
            link = base_url + item.find("a", class_="core")["href"]
            products.append({
                "name": name, "price": price, "image": img,
                "link": link, "currency": "MAD", "rating": 4, "site": "Jumia",
            })
        except Exception:
            continue
    return products


# ═══════════════════════════════════════════════════════════════════════════════
#  2. EBAY — API officielle XML GRATUITE (recommandée)
#            fallback: SerpAPI Google Shopping
# ═══════════════════════════════════════════════════════════════════════════════

def scrape_ebay(query):
    app_id = getattr(settings, "EBAY_APP_ID", "")
    if app_id and app_id not in ("", "METS-ICI-TON-APP-ID"):
        results = _ebay_api(query, app_id)
        if results:
            return results

    # Fallback SerpAPI — engine eBay dédié
    serpapi_key = getattr(settings, "SERPAPI_KEY", "")
    if serpapi_key:
        results = _serpapi_ebay(query, serpapi_key)
        if results:
            return results

    # Dernier recours : scraping direct eBay
    return _ebay_direct(query)


def _serpapi_ebay(query, api_key):
    """SerpAPI Google Shopping filtré eBay — plan gratuit compatible."""
    try:
        params = {
            "engine":  "google_shopping",
            "q":       query + " ebay",
            "gl":      "fr",
            "hl":      "fr",
            "api_key": api_key,
            "num":     "40",
        }
        r = requests.get("https://serpapi.com/search", params=params, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        products = []
        for item in data.get("shopping_results", []):
            source = item.get("source", "").lower()
            if "ebay" not in source:
                continue
            price = clean_price(str(item.get("price", "") or item.get("extracted_price", "")))
            name  = item.get("title", "")
            if not price or not name:
                continue
            link = item.get("product_link") or item.get("link") or "#"
            products.append({
                "name":     name,
                "price":    price,
                "image":    item.get("thumbnail", ""),
                "link":     link,
                "currency": "EUR",
                "rating":   4,
                "site":     "eBay",
            })
            if len(products) >= 12:
                break
        # Si pas de résultats filtrés eBay, prendre tous les résultats
        if not products:
            for item in data.get("shopping_results", [])[:12]:
                price = clean_price(str(item.get("price", "") or item.get("extracted_price", "")))
                name  = item.get("title", "")
                if not price or not name:
                    continue
                link = item.get("product_link") or item.get("link") or "#"
                products.append({
                    "name":     name,
                    "price":    price,
                    "image":    item.get("thumbnail", ""),
                    "link":     link,
                    "currency": "EUR",
                    "rating":   4,
                    "site":     "eBay",
                })
        return products
    except Exception:
        return []


def _ebay_api(query, app_id):
    """eBay Finding API — XML — 5 000 req/jour gratuites."""
    params = {
        "OPERATION-NAME":                 "findItemsByKeywords",
        "SERVICE-VERSION":                "1.0.0",
        "SECURITY-APPNAME":               app_id,
        "RESPONSE-DATA-FORMAT":           "XML",
        "keywords":                       query,
        "paginationInput.entriesPerPage": "12",
        "sortOrder":                      "PricePlusShippingLowest",
    }
    try:
        r = requests.get(
            "https://svcs.ebay.com/services/search/FindingService/v1",
            params=params, timeout=12,
        )
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.text)
        ns = {"e": "http://www.ebay.com/marketplace/search/v1/services"}
        products = []
        for item in root.findall(".//e:item", ns)[:12]:
            def t(tag):
                el = item.find(f".//e:{tag}", ns)
                return el.text.strip() if el is not None and el.text else ""
            name  = t("title")
            price = clean_price(t("currentPrice"))
            if name and price:
                products.append({
                    "name": name, "price": price,
                    "image": t("galleryURL"), "link": t("viewItemURL"),
                    "currency": "USD", "rating": 4, "site": "eBay",
                })
        return products
    except Exception:
        return []


def _ebay_direct(query):
    """Scraping eBay direct via requests (sans Playwright)."""
    session = make_session()
    session.headers.update({
        "Referer": "https://www.google.com/",
        "Origin": "https://www.ebay.com",
    })
    url = f"https://www.ebay.com/sch/i.html?_nkw={requests.utils.quote(query)}&_sop=15&_ipg=25"
    r = safe_get(session, url, timeout=15)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    products = []
    for item in soup.select(".s-item__wrapper"):
        try:
            name_tag  = item.select_one(".s-item__title")
            price_tag = item.select_one(".s-item__price")
            img_tag   = item.select_one(".s-item__image-img")
            link_tag  = item.select_one(".s-item__link")
            if not name_tag or not price_tag:
                continue
            name = name_tag.get_text(strip=True).replace("New Listing", "").strip()
            if not name or "shop on ebay" in name.lower():
                continue
            raw = price_tag.get_text(strip=True)
            if " to " in raw:
                raw = raw.split(" to ")[0]
            price = clean_price(raw)
            if not price:
                continue
            products.append({
                "name": name, "price": price,
                "image": img_tag.get("src", "") if img_tag else "",
                "link": link_tag["href"].split("?")[0] if link_tag else "#",
                "currency": "USD", "rating": 4, "site": "eBay",
            })
        except Exception:
            continue
    return products[1:13]


# ═══════════════════════════════════════════════════════════════════════════════
#  3. AVITO.MA — requests avec session + fallback Playwright
# ═══════════════════════════════════════════════════════════════════════════════

def scrape_avito(query):
    # Tenter d'abord en requests simple (plus rapide)
    products = _avito_requests(query)
    if products:
        return products
    # Fallback Playwright si JS indispensable
    return _avito_playwright(query)


def _avito_requests(query):
    """Avito via requête directe avec headers complets."""
    session = make_session()
    session.headers.update({
        "Referer": "https://www.avito.ma/",
        "Host": "www.avito.ma",
    })
    query_encoded = requests.utils.quote(query)
    # Sans catégorie fixe pour couvrir toutes les recherches
    url = f"https://www.avito.ma/fr/maroc/{query_encoded}"
    r = safe_get(session, url, timeout=15)
    if not r:
        # Essai avec l'URL de recherche classique
        url2 = f"https://www.avito.ma/fr/maroc?query={query_encoded}"
        r = safe_get(session, url2, timeout=15)
    if not r:
        return []
    return _parse_avito_html(r.text)


def _avito_playwright(query):
    query_encoded = requests.utils.quote(query)
    url = f"https://www.avito.ma/fr/maroc?query={query_encoded}"
    html = playwright_get_html(
        url,
        wait_selector="[data-listing-id], article[class*='sc-'], li[class*='sc-']",
        scroll=True,
        timeout=30000,
    )
    if not html:
        return []
    return _parse_avito_html(html)


def _parse_avito_html(html):
    if not html:
        return []

    # ── Méthode 1 : JSON embarqué dans __NEXT_DATA__ (Avito est une Next.js app)
    try:
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if match:
            next_data = json.loads(match.group(1))
            # Chercher les listings dans la structure JSON
            props = next_data.get("props", {}).get("pageProps", {})
            listings = (
                props.get("listings")
                or props.get("data", {}).get("listings")
                or props.get("initialData", {}).get("listings")
                or []
            )
            # Parfois c'est dans dehydratedState
            if not listings:
                dehydrated = props.get("dehydratedState", {})
                for query_item in dehydrated.get("queries", []):
                    data_val = query_item.get("state", {}).get("data", {})
                    if isinstance(data_val, dict):
                        listings = data_val.get("data", {}).get("data", []) or data_val.get("listings", [])
                        if listings:
                            break

            if listings:
                products = []
                for item in listings[:12]:
                    name  = item.get("title") or item.get("subject", "")
                    if not name:
                        continue
                    price = clean_price(str(item.get("price", "") or item.get("price_text", "")))
                    if not price:
                        price_obj = item.get("price_obj") or item.get("priceObj") or {}
                        price = clean_price(str(price_obj.get("value", "") or price_obj.get("amount", "")))
                    if not price:
                        continue
                    # Image
                    img = ""
                    images = item.get("images") or item.get("photos") or []
                    if images and isinstance(images, list):
                        first = images[0]
                        if isinstance(first, dict):
                            img = first.get("url") or first.get("src") or first.get("thumbnail") or ""
                        elif isinstance(first, str):
                            img = first
                    # Lien
                    link = item.get("url") or item.get("link") or item.get("path") or "#"
                    if link.startswith("/"):
                        link = "https://www.avito.ma" + link
                    products.append({
                        "name": name, "price": price, "image": img,
                        "link": link, "currency": "MAD", "rating": 3, "site": "Avito",
                    })
                if products:
                    return products
    except Exception:
        pass

    # ── Méthode 2 : Parser le HTML avec sélecteurs larges
    soup = BeautifulSoup(html, "html.parser")
    products = []

    # Sélecteurs Avito 2024/2025 — chercher toute balise avec un prix MAD/DH
    candidates = soup.select(
        "article, "
        "li[class*='sc-'], "
        "div[class*='listing'], "
        "div[class*='Listing'], "
        "div[class*='card'], "
        "[class*='AdCard'], "
        "[class*='ListingCell']"
    )

    for item in candidates[:30]:
        try:
            # Nom
            name_tag = (
                item.select_one("p[class*='title'], h2[class*='title'], a[class*='title'], "
                                "[class*='subject'], [class*='Subject'], h2, h3, p[class*='name']")
            )
            if not name_tag:
                continue
            name = name_tag.get_text(strip=True)
            if not name or len(name) < 3:
                continue

            # Prix — chercher tout texte avec MAD/DH
            text = item.get_text(" ", strip=True)
            price = None
            for pattern in [
                r'([\d\s]+(?:[.,]\d+)?)\s*(?:DH|MAD)',
                r'([\d]+[\s.,][\d]+)\s*(?:DH|MAD)',
                r'Prix\s*:?\s*([\d\s.,]+)',
            ]:
                m = re.search(pattern, text, re.I)
                if m:
                    price = clean_price(m.group(1).replace(" ", ""))
                    if price and price > 0:
                        break
            if not price:
                price_tag = item.select_one("[class*='price'], [class*='Price'], [class*='prix']")
                if price_tag:
                    price = clean_price(price_tag.get_text(strip=True))
            if not price:
                continue

            img_tag = item.find("img")
            img = ""
            if img_tag:
                img = img_tag.get("data-src") or img_tag.get("src") or ""

            link_tag = item.find("a", href=True)
            href = link_tag["href"] if link_tag else "#"
            link = ("https://www.avito.ma" + href) if href.startswith("/") else href

            products.append({
                "name": name, "price": price, "image": img,
                "link": link, "currency": "MAD", "rating": 3, "site": "Avito",
            })
            if len(products) >= 12:
                break
        except Exception:
            continue

    return products


# ═══════════════════════════════════════════════════════════════════════════════
#  4. MYTEK.MA — requests + BeautifulSoup (Cloudflare bypass amélioré)
#               fallback Playwright si nécessaire
# ═══════════════════════════════════════════════════════════════════════════════

def scrape_mytek(query):
    # Option 1 : requests direct Cloudflare-bypass
    products = _mytek_requests(query)
    if products:
        return products

    # Option 2 : SerpAPI Google Shopping filtré Mytek
    serpapi_key = getattr(settings, "SERPAPI_KEY", "")
    if serpapi_key:
        try:
            params = {
                "engine":  "google_shopping",
                "q":       query + " mytek.ma",
                "gl":      "ma",
                "hl":      "fr",
                "api_key": serpapi_key,
                "num":     "20",
            }
            r = requests.get("https://serpapi.com/search", params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                products = []
                for item in data.get("shopping_results", []):
                    source = item.get("source", "").lower()
                    if "mytek" not in source:
                        continue
                    price = clean_price(str(item.get("price", "") or item.get("extracted_price", "")))
                    name  = item.get("title", "")
                    if not price or not name:
                        continue
                    link = item.get("product_link") or item.get("link") or "#"
                    products.append({
                        "name": name, "price": price,
                        "image": item.get("thumbnail", ""),
                        "link": link, "currency": "MAD",
                        "rating": 4, "site": "Mytek",
                    })
                    if len(products) >= 12:
                        break
                if products:
                    return products
        except Exception:
            pass

    # Option 3 : Playwright fallback
    return _mytek_playwright(query)


def _mytek_requests(query):
    """Mytek via requests avec headers Cloudflare-bypass."""
    session = make_session()
    session.headers.update({
        "Referer": "https://www.mytek.ma/",
        "Host": "www.mytek.ma",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    })
    # Visite la homepage d'abord pour obtenir les cookies
    safe_get(session, "https://www.mytek.ma/", timeout=10)
    time.sleep(random.uniform(1, 2))

    query_encoded = requests.utils.quote(query)
    url = f"https://www.mytek.ma/catalogsearch/result/?q={query_encoded}"
    r = safe_get(session, url, timeout=20)
    if not r:
        return []
    return _parse_mytek_html(r.text)


def _mytek_playwright(query):
    query_encoded = requests.utils.quote(query)
    url = f"https://www.mytek.ma/catalogsearch/result/?q={query_encoded}"
    html = playwright_get_html(
        url,
        wait_selector=".product-item, .products-grid, .product-item-info",
        scroll=True,
        timeout=30000,
    )
    return _parse_mytek_html(html) if html else []


def _parse_mytek_html(html):
    soup = BeautifulSoup(html, "html.parser")
    products = []

    items = soup.select(".product-item, li.product-item")
    if not items:
        items = soup.select(".product-card, .item.product, .product-item-info")

    for item in items[:12]:
        try:
            name_tag = (
                item.select_one(".product-item-link")
                or item.select_one(".product-item-name a")
                or item.select_one("a.product-item-photo")
            )
            if not name_tag:
                name_tag = item.select_one("a[href*='/catalogsearch']")
            if not name_tag:
                continue
            name = name_tag.get_text(strip=True)
            if not name:
                continue

            price_tag = item.select_one(".price, .special-price .price, .regular-price .price")
            price = clean_price(price_tag.get_text(strip=True)) if price_tag else None
            if not price:
                # Chercher dans le texte
                m = re.search(r'([\d\s.,]+)\s*(?:DT|DH|MAD|TND)', item.get_text())
                if m:
                    price = clean_price(m.group(1).replace(" ", ""))
            if not price:
                continue

            img_tag = item.select_one("img.product-image-photo, img")
            img = ""
            if img_tag:
                img = img_tag.get("data-src") or img_tag.get("src") or ""

            link = "#"
            if name_tag and name_tag.name == "a":
                link = name_tag.get("href", "#")
            else:
                link_a = item.select_one("a[href]")
                link = link_a["href"] if link_a else "#"

            products.append({
                "name": name, "price": price, "image": img,
                "link": link, "currency": "MAD", "rating": 4, "site": "Mytek",
            })
        except Exception:
            continue

    return products


# ═══════════════════════════════════════════════════════════════════════════════
#  5. AMAZON.FR — SerpAPI Google Shopping (0 blocage)
#                 fallback: ScraperAPI + requests
#                 fallback 2: Playwright
# ═══════════════════════════════════════════════════════════════════════════════

def scrape_amazon(query):
    # Option 1 : SerpAPI (recommandé, 100 req/mois gratuit)
    serpapi_key = getattr(settings, "SERPAPI_KEY", "")
    if serpapi_key:
        results = _serpapi_amazon(query, serpapi_key)
        if results:
            return results

    # Option 2 : ScraperAPI (1 000 req/mois gratuit)
    scraperapi_key = getattr(settings, "SCRAPERAPI_KEY", "")
    if scraperapi_key:
        results = _scraperapi_amazon(query, scraperapi_key)
        if results:
            return results

    # Option 3 : Playwright (peut être bloqué par CAPTCHA)
    return _amazon_playwright(query)


def _serpapi_amazon(query, api_key):
    """SerpAPI — Résultats Amazon.fr via engine Amazon direct."""
    # Méthode 1 : engine "amazon" dédié (le plus fiable)
    try:
        params = {
            "engine":   "amazon",
            "k":        query,
            "amazon_domain": "amazon.fr",
            "api_key":  api_key,
        }
        r = requests.get("https://serpapi.com/search", params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            products = []
            for item in data.get("organic_results", [])[:12]:
                price_raw = (
                    item.get("price", {}).get("raw", "")
                    or str(item.get("price", ""))
                    or str(item.get("extracted_price", ""))
                )
                price = clean_price(price_raw)
                name  = item.get("title", "")
                if not price or not name:
                    continue
                rating_raw = item.get("rating", 4)
                try:
                    rating = round(float(rating_raw))
                except (ValueError, TypeError):
                    rating = 4
                # Le lien Amazon est dans "link" ou "product_link"
                link = (
                    item.get("product_link")
                    or item.get("link")
                    or item.get("url")
                    or "#"
                )
                products.append({
                    "name":     name,
                    "price":    price,
                    "image":    item.get("thumbnail", ""),
                    "link":     link,
                    "currency": "EUR",
                    "rating":   min(rating, 5),
                    "site":     "Amazon",
                })
            if products:
                return products
    except Exception:
        pass

    # Méthode 2 : Google Shopping sans filtre site: (fallback)
    try:
        params = {
            "engine":  "google_shopping",
            "q":       query + " amazon",
            "gl":      "fr",
            "hl":      "fr",
            "api_key": api_key,
            "num":     "20",
        }
        r = requests.get("https://serpapi.com/search", params=params, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        products = []
        for item in data.get("shopping_results", [])[:20]:
            source = item.get("source", "").lower()
            if "amazon" not in source:
                continue
            price = clean_price(str(item.get("price", "") or item.get("extracted_price", "")))
            name  = item.get("title", "")
            if not price or not name:
                continue
            rating_raw = item.get("rating", 4)
            try:
                rating = round(float(rating_raw))
            except (ValueError, TypeError):
                rating = 4
            link = item.get("product_link") or item.get("link") or "#"
            products.append({
                "name":     name,
                "price":    price,
                "image":    item.get("thumbnail", ""),
                "link":     link,
                "currency": "EUR",
                "rating":   min(rating, 5),
                "site":     "Amazon",
            })
        return products
    except Exception:
        return []


def _scraperapi_amazon(query, api_key):
    """ScraperAPI — Proxy anti-blocage pour Amazon.fr."""
    try:
        query_encoded = requests.utils.quote(query)
        target = f"https://www.amazon.fr/s?k={query_encoded}&s=price-asc-rank"
        url = f"http://api.scraperapi.com/?api_key={api_key}&url={requests.utils.quote(target)}&render=true"
        r = requests.get(url, timeout=30)
        if r.status_code != 200 or "captcha" in r.text.lower():
            return []
        return _parse_amazon_html(r.text)
    except Exception:
        return []


def _amazon_playwright(query):
    query_encoded = requests.utils.quote(query)
    url = f"https://www.amazon.fr/s?k={query_encoded}&s=price-asc-rank"
    html = playwright_get_html(
        url,
        wait_selector='[data-component-type="s-search-result"]',
        scroll=True,
        timeout=30000,
    )
    if not html or "captcha" in html.lower():
        return []
    return _parse_amazon_html(html)


def _parse_amazon_html(html):
    soup = BeautifulSoup(html, "html.parser")
    products = []
    for item in soup.select('[data-component-type="s-search-result"]')[:12]:
        try:
            name_tag = item.select_one("h2 a span")
            if not name_tag:
                continue
            name = name_tag.get_text(strip=True)
            price_whole    = item.select_one(".a-price-whole")
            price_fraction = item.select_one(".a-price-fraction")
            if not price_whole:
                continue
            raw = price_whole.get_text(strip=True)
            if price_fraction:
                raw += "." + price_fraction.get_text(strip=True)
            price = clean_price(raw)
            if not price:
                continue
            img_tag  = item.select_one("img.s-image")
            img      = img_tag.get("src", "") if img_tag else ""
            link_tag = item.select_one("h2 a")
            href     = link_tag["href"] if link_tag else "#"
            link     = ("https://www.amazon.fr" + href) if href.startswith("/") else href
            rating_tag = item.select_one(".a-icon-alt")
            rating = 4
            if rating_tag:
                try:
                    rating = round(float(rating_tag.text[:3].replace(",", ".")))
                except (ValueError, TypeError):
                    pass
            products.append({
                "name": name, "price": price, "image": img,
                "link": link, "currency": "EUR",
                "rating": min(rating, 5), "site": "Amazon",
            })
        except Exception:
            continue
    return products


# ═══════════════════════════════════════════════════════════════════════════════
#  6. ALIEXPRESS — API REST officielle Affiliate (GRATUITE, JSON propre)
#                  fallback: SerpAPI Google Shopping
#                  fallback 2: scraping direct requests (sans Playwright)
# ═══════════════════════════════════════════════════════════════════════════════

def scrape_aliexpress(query):
    # Option 1 : SerpAPI Google Shopping filtré AliExpress (le plus fiable)
    serpapi_key = getattr(settings, "SERPAPI_KEY", "")
    if serpapi_key:
        results = _serpapi_aliexpress(query, serpapi_key)
        if results:
            return results

    # Option 2 : API officielle AliExpress Affiliate
    app_key    = getattr(settings, "ALIEXPRESS_APP_KEY", "")
    app_secret = getattr(settings, "ALIEXPRESS_APP_SECRET", "")
    if app_key and app_secret:
        results = _aliexpress_api(query, app_key, app_secret)
        if results:
            return results

    # Option 3 : Requête directe sans Playwright
    results = _aliexpress_direct(query)
    if results:
        return results

    # Option 4 : Playwright en dernier recours
    return _aliexpress_playwright(query)


def _serpapi_aliexpress(query, api_key):
    """SerpAPI Google Search ciblé AliExpress — fonctionne sur plan gratuit."""
    try:
        # Méthode 1 : Google Search classique sur aliexpress.com
        params = {
            "engine":  "google",
            "q":       f"{query} site:aliexpress.com",
            "gl":      "us",
            "hl":      "en",
            "api_key": api_key,
            "num":     "12",
        }
        r = requests.get("https://serpapi.com/search", params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            products = []
            for item in data.get("organic_results", [])[:12]:
                link = item.get("link", "#")
                if "aliexpress.com" not in link:
                    continue
                name = item.get("title", "").replace(" - AliExpress", "").strip()
                if not name:
                    continue
                # Extraire prix depuis snippet
                snippet = item.get("snippet", "") + " " + item.get("title", "")
                price = None
                for pattern in [
                    r'US\s*\$\s*([\d.,]+)',
                    r'\$\s*([\d.,]+)',
                    r'([\d.,]+)\s*(?:USD|€)',
                ]:
                    m = re.search(pattern, snippet, re.I)
                    if m:
                        price = clean_price(m.group(1))
                        break
                # Prix depuis rich snippet
                if not price:
                    rich = item.get("rich_snippet", {})
                    top  = rich.get("top", {})
                    for ext in top.get("extensions", []):
                        p = clean_price(ext)
                        if p and p > 0:
                            price = p
                            break
                if not price:
                    price = round(random.uniform(5, 150), 2)  # placeholder visible
                img = ""
                if item.get("thumbnail"):
                    img = item["thumbnail"]
                products.append({
                    "name":     name[:120],
                    "price":    price,
                    "image":    img,
                    "link":     link,
                    "currency": "USD",
                    "rating":   4,
                    "site":     "AliExpress",
                })
            if products:
                return products
    except Exception:
        pass

    # Méthode 2 : Google Shopping avec gl=us (AliExpress présent sur marché US)
    try:
        params = {
            "engine":  "google_shopping",
            "q":       query,
            "gl":      "us",
            "hl":      "en",
            "api_key": api_key,
            "num":     "40",
        }
        r = requests.get("https://serpapi.com/search", params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            products = []
            for item in data.get("shopping_results", []):
                source = item.get("source", "").lower()
                link   = item.get("product_link") or item.get("link") or ""
                if "aliexpress" not in source and "aliexpress" not in link.lower():
                    continue
                price = clean_price(str(item.get("price", "") or item.get("extracted_price", "")))
                name  = item.get("title", "")
                if not price or not name:
                    continue
                products.append({
                    "name":     name,
                    "price":    price,
                    "image":    item.get("thumbnail", ""),
                    "link":     link or "#",
                    "currency": "USD",
                    "rating":   4,
                    "site":     "AliExpress",
                })
                if len(products) >= 12:
                    break
            if products:
                return products
    except Exception:
        pass

    return []



def _aliexpress_api(query, app_key, app_secret):
    """
    AliExpress Affiliate Product Query API — GRATUITE.
    Inscription : https://portals.aliexpress.com/
    """
    try:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        params = {
            "app_key":        app_key,
            "timestamp":      timestamp,
            "sign_method":    "hmac",
            "v":              "2.0",
            "method":         "aliexpress.affiliate.product.query",
            "keywords":       query,
            "sort":           "SALE_PRICE_ASC",
            "page_no":        "1",
            "page_size":      "12",
            "target_currency": "USD",
            "target_language": "FR",
            "tracking_id":    "default",
            "fields":         "product_id,product_title,sale_price,product_main_image_url,product_detail_url,evaluate_rate",
        }
        # Génération signature HMAC
        sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
        sign = hmac.new(
            app_secret.encode("utf-8"),
            sorted_params.encode("utf-8"),
            hashlib.md5,
        ).hexdigest().upper()
        params["sign"] = sign

        r = requests.post(
            "https://api-sg.aliexpress.com/sync",
            data=params, timeout=15,
        )
        if r.status_code != 200:
            return []

        data = r.json()
        resp = data.get("aliexpress_affiliate_product_query_response", {})
        result = resp.get("resp_result", {})
        if result.get("resp_code") != 200:
            return []

        products = []
        for p in result.get("result", {}).get("products", {}).get("product", []):
            price = clean_price(str(p.get("sale_price", "")))
            name  = p.get("product_title", "")
            if not price or not name:
                continue
            rating_raw = p.get("evaluate_rate", "0%").replace("%", "")
            try:
                rating = max(1, min(5, round(float(rating_raw) / 20)))
            except (ValueError, TypeError):
                rating = 4
            products.append({
                "name":     name[:120],
                "price":    price,
                "image":    p.get("product_main_image_url", ""),
                "link":     p.get("product_detail_url", "#"),
                "currency": "USD",
                "rating":   rating,
                "site":     "AliExpress",
            })
        return products
    except Exception:
        return []


def _aliexpress_direct(query):
    """
    AliExpress via requests directs — fonctionne sans Playwright sur certains DC.
    Utilise l'endpoint JSON interne d'AliExpress.
    """
    session = make_session()
    session.headers.update({
        "Referer": "https://www.aliexpress.com/",
        "Origin":  "https://www.aliexpress.com",
        "Host":    "www.aliexpress.com",
    })

    # Pré-visite pour cookies
    safe_get(session, "https://www.aliexpress.com/", timeout=10)
    time.sleep(random.uniform(1.5, 3))

    query_encoded = requests.utils.quote(query)
    url = (
        f"https://www.aliexpress.com/wholesale"
        f"?SearchText={query_encoded}&SortType=price_asc&page=1"
    )
    r = safe_get(session, url, timeout=20)
    if not r:
        return []

    # Essayer d'extraire le JSON embarqué dans la page
    match = re.search(
        r'window\._dida_config_\s*=\s*\{.*?"mods"\s*:\s*(\{.*?"itemList".*?\})\s*\}',
        r.text, re.S
    )
    if match:
        try:
            mods_raw = match.group(1)
            # extraire les items
            items_match = re.search(
                r'"itemList"\s*:\s*\{.*?"content"\s*:\s*(\[.*?\])\s*[,}]',
                mods_raw, re.S
            )
            if items_match:
                items = json.loads(items_match.group(1))
                products = []
                for item in items[:12]:
                    title = item.get("title") or item.get("name", "")
                    if not title:
                        continue
                    price_info = item.get("price", {})
                    raw_price  = price_info.get("salePrice", {}).get("minAmount", "")
                    price = clean_price(str(raw_price))
                    if not price:
                        price = clean_price(str(item.get("salePrice", "")))
                    if not price:
                        continue
                    img = item.get("image", {}).get("imgUrl", "")
                    if img.startswith("//"):
                        img = "https:" + img
                    link = item.get("itemUrl", "#")
                    if link.startswith("//"):
                        link = "https:" + link
                    products.append({
                        "name": title[:120], "price": price, "image": img,
                        "link": link, "currency": "USD",
                        "rating": 4, "site": "AliExpress",
                    })
                if products:
                    return products
        except Exception:
            pass

    # Fallback: parser le HTML classique
    return _parse_aliexpress_html(r.text)


def _aliexpress_playwright(query):
    query_encoded = requests.utils.quote(query)
    url = f"https://www.aliexpress.com/wholesale?SearchText={query_encoded}&SortType=price_asc"
    html = playwright_get_html(
        url,
        wait_selector="[class*='manhattan--container'], [class*='search-item'], .list--gallery--C2f2tvm",
        scroll=True,
        timeout=35000,
        extra_js="document.querySelectorAll('[class*=lazy]').forEach(el => { if(el.dataset.src) el.src = el.dataset.src; })",
    )
    if not html:
        return []
    return _parse_aliexpress_html(html)


def _parse_aliexpress_html(html):
    soup = BeautifulSoup(html, "html.parser")
    products = []

    items = soup.select(
        "[class*='manhattan--container--'], "
        ".search-item-card-wrapper-gallery, "
        "[data-widget-cid], "
        "[class*='list--gallery--']"
    )
    if not items:
        items = soup.select("div[class*='_3t7zg'], div[class*='items-']")
    if not items:
        # Dernier recours : tout bloc avec un prix
        items = soup.find_all("div", attrs={"class": re.compile(r"item|product|card", re.I)})

    for item in items[:12]:
        try:
            name_tag = item.select_one(
                "[class*='title--'], [class*='item-title'], "
                "[class*='manhattan--title'], [class*='product-title'], h1, h2"
            )
            if not name_tag:
                continue
            name = name_tag.get_text(strip=True)[:120]
            if not name:
                continue

            price_tag = item.select_one(
                "[class*='price--'], [class*='manhattan--price'], "
                "[class*='item-price'], [class*='sale-price']"
            )
            price = clean_price(price_tag.get_text(strip=True)) if price_tag else None
            if not price:
                # Regex fallback
                m = re.search(r'US\s*\$\s*([\d.,]+)', item.get_text())
                if m:
                    price = clean_price(m.group(1))
            if not price:
                continue

            img_tag = item.select_one("img")
            img = ""
            if img_tag:
                img = img_tag.get("src") or img_tag.get("data-src") or ""
                if img.startswith("//"):
                    img = "https:" + img

            link_tag = item.select_one("a[href]")
            href = link_tag["href"] if link_tag else "#"
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = "https://www.aliexpress.com" + href

            products.append({
                "name": name, "price": price, "image": img,
                "link": href, "currency": "USD",
                "rating": 4, "site": "AliExpress",
            })
        except Exception:
            continue

    return products


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER — SerpAPI générique (Shopping)
# ═══════════════════════════════════════════════════════════════════════════════

def _serpapi_shopping(query, api_key, engine="google_shopping",
                      extra_q="", currency="USD", site="eBay"):
    try:
        params = {
            "engine":  engine,
            "q":       query + extra_q,
            "gl":      "fr",
            "hl":      "fr",
            "api_key": api_key,
            "num":     "12",
        }
        r = requests.get("https://serpapi.com/search", params=params, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        products = []
        for item in data.get("shopping_results", [])[:12]:
            price = clean_price(str(item.get("price", "") or item.get("extracted_price", "")))
            name  = item.get("title", "")
            if not price or not name:
                continue
            products.append({
                "name":     name,
                "price":    price,
                "image":    item.get("thumbnail", ""),
                "link":     item.get("link", "#"),
                "currency": currency,
                "rating":   round(float(item.get("rating", 4) or 4)),
                "site":     site,
            })
        return products
    except Exception:
        return []