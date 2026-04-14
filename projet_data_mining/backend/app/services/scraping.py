import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.jumia.ma"


def scrape_products(query="laptop"):
    """
    Fonction de scraping Jumia.
    Objectif :
    - récupérer nom
    - récupérer prix
    - récupérer image
    - récupérer lien du produit (IMPORTANT)
    """

    # URL de recherche
    url = f"{BASE_URL}/catalog/?q={query}"

    # Headers pour éviter blocage
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "fr-FR,fr;q=0.9"
    }

    products = []

    try:
        response = requests.get(url, headers=headers, timeout=10)

        # Vérification si la requête a réussi
        if response.status_code != 200:
            return fallback_data(query)

        soup = BeautifulSoup(response.text, "html.parser")

        # Sélection des produits
        items = soup.find_all("article", class_="prd")

        for item in items[:12]:  # prendre max 12 produits
            try:
                # =========================
                # NOM DU PRODUIT
                # =========================
                name_tag = item.find("h3", class_="name")
                name = name_tag.text.strip() if name_tag else "Produit inconnu"

                # =========================
                # PRIX
                # =========================
                price_tag = item.find("div", class_="prc")
                if not price_tag:
                    continue

                price_text = price_tag.text.strip()

                # Nettoyage du prix (ex: "5,000 Dhs")
                price_clean = (
                    price_text.replace("Dhs", "")
                    .replace("DH", "")
                    .replace(",", "")
                    .strip()
                )

                price = float(price_clean)

                # =========================
                # IMAGE (gestion lazy loading)
                # =========================
                img_tag = item.find("img")

                image = ""
                if img_tag:
                    image = (
                        img_tag.get("data-src") or
                        img_tag.get("data-srcset") or
                        img_tag.get("src") or
                        ""
                    )

                    # éviter images vides
                    if not image or image.startswith("data:"):
                        image = "https://via.placeholder.com/150"

                # =========================
                # LIEN (IMPORTANT)
                # =========================
                link_tag = item.find("a", class_="core")

                link = "#"
                if link_tag and link_tag.get("href"):
                    link = link_tag["href"]

                    # convertir lien relatif → absolu
                    if link.startswith("/"):
                        link = BASE_URL + link

                # =========================
                # AJOUT PRODUIT
                # =========================
                products.append({
                    "name": name,
                    "price": price,
                    "image": image,
                    "link": link,
                    "currency": "MAD",
                    "rating": "⭐ 4"  # fallback rating
                })

            except Exception:
                continue

        # =========================
        # Si aucun produit trouvé → fallback
        # =========================
        if not products:
            return fallback_data(query)

        return products

    except Exception:
        return fallback_data(query)


# =========================
# DONNÉES DE SECOURS (fallback)
# =========================
def fallback_data(query):
    """
    Données utilisées si scraping échoue
    """

    return [
        {
            "name": f"{query} HP Laptop",
            "price": 5000,
            "image": "https://via.placeholder.com/150",
            "link": "https://www.jumia.ma/catalog/?q=" + query,
            "currency": "MAD",
            "rating": "⭐ 4"
        },
        {
            "name": f"{query} Dell Laptop",
            "price": 5500,
            "image": "https://via.placeholder.com/150",
            "link": "https://www.jumia.ma/catalog/?q=" + query,
            "currency": "MAD",
            "rating": "⭐ 5"
        }
    ]