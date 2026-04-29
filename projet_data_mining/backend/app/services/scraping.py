from .scrapingavito import scrape_avito
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.jumia.ma"


# =========================
# SCRAPING JUMIA
# =========================
def scrape_jumia(query="laptop"):

    url = f"{BASE_URL}/catalog/?q={query}"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "fr-FR,fr;q=0.9"
    }

    products = []

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return fallback_data(query)

        soup = BeautifulSoup(response.text, "html.parser")

        items = soup.find_all("article", class_="prd")

        for item in items[:12]:
            try:
                name_tag = item.find("h3", class_="name")
                name = name_tag.text.strip() if name_tag else "Produit inconnu"

                price_tag = item.find("div", class_="prc")
                if not price_tag:
                    continue

                price_text = price_tag.text.strip()
                price_clean = (
                    price_text.replace("Dhs", "")
                    .replace("DH", "")
                    .replace(",", "")
                    .strip()
                )

                price = float(price_clean)

                img_tag = item.find("img")

                image = ""
                if img_tag:
                    image = (
                        img_tag.get("data-src") or
                        img_tag.get("src") or
                        ""
                    )

                if not image or image.startswith("data:"):
                    image = "https://via.placeholder.com/150"

                link_tag = item.find("a", class_="core")

                link = "#"
                if link_tag and link_tag.get("href"):
                    link = link_tag["href"]
                    if link.startswith("/"):
                        link = BASE_URL + link

                products.append({
                    "name": name,
                    "price": price,
                    "image": image,
                    "link": link,
                    "currency": "MAD",
                    "rating": 4
                })

            except Exception:
                continue

        if not products:
            return fallback_data(query)

        return products

    except Exception:
        return fallback_data(query)


# =========================
# CONTROLLER PRINCIPAL
# =========================
def scrape_products(query="laptop", source="jumia"):

    if source == "jumia":
        return scrape_jumia(query)

    elif source == "avito":
        return scrape_avito(query)

    elif source == "all":
        return scrape_jumia(query) + scrape_avito(query)

    return scrape_jumia(query)


# =========================
# FALLBACK
# =========================
def fallback_data(query):
    return [
        {
            "name": f"{query} HP Laptop",
            "price": 5000,
            "image": "https://via.placeholder.com/150",
            "link": "https://www.jumia.ma/catalog/?q=" + query,
            "currency": "MAD",
            "rating": 4
        }
    ]