import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://www.avito.ma"


def clean_price(text):
    match = re.search(r"(\d[\d\s\u00a0]{1,12})\s*(DH|Dhs|MAD)", text)

    if not match:
        return None

    price_text = match.group(1)
    price_text = price_text.replace("\u00a0", "").replace(" ", "")

    if not price_text.isdigit():
        return None

    price = float(price_text)

    if price <= 0 or price > 1000000:
        return None

    return price


def clean_name(text, price):
    text = re.sub(r"(\d[\d\s\u00a0]*)\s*(DH|Dhs|MAD)", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > 120:
        text = text[:120]

    return text if text else "Produit Avito"


def scrape_avito(query="laptop"):
    url = f"{BASE_URL}/fr/maroc?q={query}"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "fr-FR,fr;q=0.9"
    }

    products = []

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        items = soup.find_all("a", href=True)

        for item in items:
            text = item.get_text(" ", strip=True)

            if "DH" not in text and "MAD" not in text:
                continue

            price = clean_price(text)

            if price is None:
                continue

            name = clean_name(text, price)

            img_tag = item.find("img")
            image = "https://via.placeholder.com/150"

            if img_tag:
                image = (
                    img_tag.get("src")
                    or img_tag.get("data-src")
                    or img_tag.get("data-lazy")
                    or "https://via.placeholder.com/150"
                )

            link = item.get("href", "#")

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

            if len(products) >= 12:
                break

        return products

    except Exception:
        return []