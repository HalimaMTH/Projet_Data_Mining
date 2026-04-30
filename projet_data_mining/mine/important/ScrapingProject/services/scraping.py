import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"
}


def clean_price(text):
    if not text:
        return 0

    text = (
        text.replace("Dhs", "")
        .replace("DH", "")
        .replace("MAD", "")
        .replace("$", "")
        .replace("US", "")
        .replace("£", "")
        .replace("€", "")
        .replace(",", "")
        .replace("\xa0", "")
        .replace(" ", "")
    )

    number = "".join(c for c in text if c.isdigit() or c == ".")

    try:
        return float(number)
    except:
        return 0


def get_soup_requests(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print("Request blocked:", r.status_code, url)
            return None
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print("Request error:", e)
        return None


def get_soup_playwright(url, wait=3000):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=HEADERS["User-Agent"],
                viewport={"width": 1920, "height": 1080}
            )
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(wait)
            html = page.content()
            browser.close()
            return BeautifulSoup(html, "html.parser")
    except Exception as e:
        print("Playwright error:", e)
        return None


def scrape_products(query, site):
    site = site.lower()

    routers = {
        "jumia": scrape_jumia,
        "books": scrape_books,
        "avito": scrape_avito,
        "ebay": scrape_ebay,
        "amazon": scrape_amazon,
        "aliexpress": scrape_aliexpress,
        "noon": scrape_noon,
        "etsy": scrape_etsy,
    }

    scraper = routers.get(site)

    if not scraper:
        return []

    return scraper(query)


def scrape_jumia(query):
    BASE = "https://www.jumia.ma"
    url = f"{BASE}/catalog/?q={quote_plus(query)}"

    soup = get_soup_requests(url)
    if not soup:
        return []

    products = []
    items = soup.find_all("article", class_="prd")

    for item in items[:12]:
        name_tag = item.find("h3", class_="name")
        price_tag = item.find("div", class_="prc")
        link_tag = item.find("a", class_="core")
        img_tag = item.find("img")

        if not name_tag or not price_tag:
            continue

        name = name_tag.get_text(strip=True)
        price = clean_price(price_tag.get_text())

        if price == 0:
            continue

        link = "#"
        if link_tag and link_tag.get("href"):
            link = link_tag["href"]
            if link.startswith("/"):
                link = BASE + link

        image = ""
        if img_tag:
            image = img_tag.get("data-src") or img_tag.get("src") or ""

        products.append({
            "name": name,
            "price": price,
            "currency": "MAD",
            "image": image,
            "link": link,
            "site": "Jumia"
        })

    return products


def scrape_books(query):
    BASE = "https://books.toscrape.com"
    products = []

    for page_num in range(1, 6):
        url = f"{BASE}/catalogue/page-{page_num}.html"
        soup = get_soup_requests(url)

        if not soup:
            continue

        items = soup.find_all("article", class_="product_pod")

        for item in items:
            name_tag = item.find("h3").find("a")

            if not name_tag:
                continue

            name = name_tag["title"]

            if query.lower() not in name.lower():
                continue

            price_tag = item.find("p", class_="price_color")
            price = clean_price(price_tag.get_text()) * 15

            img_tag = item.find("img")
            image = BASE + "/" + img_tag["src"].replace("../", "") if img_tag else ""

            link = BASE + "/catalogue/" + name_tag["href"].replace("../", "")

            products.append({
                "name": name,
                "price": round(price, 2),
                "currency": "MAD",
                "image": image,
                "link": link,
                "site": "Books"
            })

            if len(products) >= 12:
                return products

    return products


def scrape_avito(query):
    BASE = "https://www.avito.ma"
    url = f"{BASE}/fr/maroc/tout?search[keywords]={quote_plus(query)}"

    soup = get_soup_playwright(url, wait=5000)
    if not soup:
        return []

    products = []
    links = soup.find_all("a", href=True)

    for a in links:
        text = a.get_text(" ", strip=True)

        if not text:
            continue

        if query.lower() not in text.lower():
            continue

        href = a.get("href")
        if not href:
            continue

        link = BASE + href if href.startswith("/") else href

        img_tag = a.find("img")
        image = img_tag.get("src") if img_tag else ""

        products.append({
            "name": text[:100],
            "price": 0,
            "currency": "MAD",
            "image": image,
            "link": link,
            "site": "Avito"
        })

        if len(products) >= 12:
            break

    return products


def scrape_ebay(query):
    BASE = "https://www.ebay.com"
    url = f"{BASE}/sch/i.html?_nkw={quote_plus(query)}"

    soup = get_soup_playwright(url)
    if not soup:
        return []

    products = []
    items = soup.find_all("li", class_="s-item")

    for item in items[:20]:
        name_tag = item.find("div", class_="s-item__title")
        price_tag = item.find("span", class_="s-item__price")
        link_tag = item.find("a", class_="s-item__link")
        img_tag = item.find("img")

        if not name_tag or not price_tag:
            continue

        name = name_tag.get_text(strip=True)

        if name.lower() == "shop on ebay":
            continue

        price = clean_price(price_tag.get_text()) * 10

        image = img_tag.get("src") if img_tag else ""
        link = link_tag.get("href") if link_tag else "#"

        products.append({
            "name": name,
            "price": round(price, 2),
            "currency": "MAD",
            "image": image,
            "link": link,
            "site": "eBay"
        })

        if len(products) >= 12:
            break

    return products


def scrape_amazon(query):
    BASE = "https://www.amazon.com"
    url = f"{BASE}/s?k={quote_plus(query)}"

    soup = get_soup_playwright(url, wait=5000)
    if not soup:
        return []

    products = []
    items = soup.find_all("div", {"data-component-type": "s-search-result"})

    for item in items[:12]:
        name_tag = item.find("span", class_="a-size-medium") or item.find("span", class_="a-size-base-plus")
        price_tag = item.find("span", class_="a-price-whole")
        img_tag = item.find("img", class_="s-image")
        link_tag = item.find("a", class_="a-link-normal")

        if not name_tag or not price_tag:
            continue

        name = name_tag.get_text(strip=True)
        price = clean_price(price_tag.get_text()) * 10

        image = img_tag.get("src") if img_tag else ""

        link = "#"
        if link_tag and link_tag.get("href"):
            link = BASE + link_tag["href"]

        products.append({
            "name": name,
            "price": round(price, 2),
            "currency": "MAD",
            "image": image,
            "link": link,
            "site": "Amazon"
        })

    return products


def scrape_aliexpress(query):
    BASE = "https://www.aliexpress.com"
    url = f"{BASE}/wholesale?SearchText={quote_plus(query)}"

    soup = get_soup_playwright(url, wait=7000)
    if not soup:
        return []

    products = []
    links = soup.find_all("a", href=True)

    for a in links:
        href = a.get("href", "")

        if "/item/" not in href:
            continue

        text = a.get_text(" ", strip=True)

        if not text:
            continue

        if href.startswith("//"):
            link = "https:" + href
        elif href.startswith("/"):
            link = BASE + href
        else:
            link = href

        img_tag = a.find("img")
        image = ""
        if img_tag:
            image = img_tag.get("src") or img_tag.get("data-src") or ""
            if image.startswith("//"):
                image = "https:" + image

        products.append({
            "name": text[:100],
            "price": 0,
            "currency": "MAD",
            "image": image,
            "link": link,
            "site": "AliExpress"
        })

        if len(products) >= 12:
            break

    return products


def scrape_noon(query):
    BASE = "https://www.noon.com"
    url = f"{BASE}/egypt-en/search/?q={quote_plus(query)}"

    soup = get_soup_playwright(url, wait=5000)
    if not soup:
        return []

    products = []
    links = soup.find_all("a", href=True)

    for a in links:
        text = a.get_text(" ", strip=True)

        if not text:
            continue

        if query.lower() not in text.lower():
            continue

        href = a.get("href")
        link = BASE + href if href.startswith("/") else href

        img_tag = a.find("img")
        image = img_tag.get("src") if img_tag else ""

        products.append({
            "name": text[:100],
            "price": 0,
            "currency": "MAD",
            "image": image,
            "link": link,
            "site": "Noon"
        })

        if len(products) >= 12:
            break

    return products


def scrape_etsy(query):
    BASE = "https://www.etsy.com"
    url = f"{BASE}/search?q={quote_plus(query)}"

    soup = get_soup_playwright(url, wait=5000)
    if not soup:
        return []

    products = []
    items = soup.find_all(attrs={"data-listing-id": True})

    for item in items[:12]:
        text = item.get_text(" ", strip=True)

        if not text:
            continue

        price = 0
        price_tag = item.find("span", class_=lambda c: c and "currency-value" in c)

        if price_tag:
            price = clean_price(price_tag.get_text()) * 10

        link_tag = item.find("a", href=True)
        link = link_tag["href"] if link_tag else "#"

        img_tag = item.find("img")
        image = img_tag.get("src") if img_tag else ""

        products.append({
            "name": text[:100],
            "price": round(price, 2),
            "currency": "MAD",
            "image": image,
            "link": link,
            "site": "Etsy"
        })

    return products


if __name__ == "__main__":
    query = input("Produit à chercher: ")

    sites = [
        "jumia",
        "avito",
        "books",
        "ebay",
        "amazon",
        "aliexpress",
        "noon",
        "etsy"
    ]

    for site in sites:
        print("\n==========================")
        print("SITE:", site.upper())
        print("==========================")

        products = scrape_products(query, site)

        if not products:
            print("Aucun produit trouvé ou site bloqué.")
        else:
            for p in products:
                print(p["name"])
                print(p["price"], p["currency"])
                print(p["link"])
                print("------------------")