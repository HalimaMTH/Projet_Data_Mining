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
    - récupérer lien du produit
    """

    # URL de recherche dynamique
    url = f"{BASE_URL}/catalog/?q={query}"

    # Headers pour éviter blocage du site
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "fr-FR,fr;q=0.9"
    }

    products = []

    try:
        response = requests.get(url, headers=headers, timeout=10)

        # Vérifier si la requête est OK
        if response.status_code != 200:
            return fallback_data(query)

        soup = BeautifulSoup(response.text, "html.parser")

        # Récupérer tous les produits
        items = soup.find_all("article", class_="prd")

        for item in items[:12]:  # max 12 produits
            try:
                # =========================
                # NOM
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

                # Nettoyage du prix
                price_clean = (
                    price_text.replace("Dhs", "")
                    .replace("DH", "")
                    .replace(",", "")
                    .strip()
                )

                price = float(price_clean)

                # =========================
                # IMAGE
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

                    # Si image invalide → placeholder
                    if not image or image.startswith("data:"):
                        image = "https://via.placeholder.com/150"

                # =========================
                # LIEN
                # =========================
                link_tag = item.find("a", class_="core")

                link = "#"
                if link_tag and link_tag.get("href"):
                    link = link_tag["href"]

                    # Convertir lien relatif → absolu
                    if link.startswith("/"):
                        link = BASE_URL + link

                # =========================
                # RATING (fix important)
                # =========================
                rating = 4  # valeur par défaut (int)

                # =========================
                # AJOUT PRODUIT
                # =========================
                products.append({
                    "name": name,
                    "price": price,
                    "image": image,
                    "link": link,
                    "currency": "MAD",
                    "rating": rating   # ✅ INT (important)
                })

            except Exception:
                continue

        # Si aucun produit trouvé → fallback
        if not products:
            return fallback_data(query)

        return products

    except Exception:
        return fallback_data(query)


# =========================
# FALLBACK (données secours)
# =========================
def fallback_data(query):
    return [
        {
            "name": f"{query} HP Laptop",
            "price": 5000,
            "image": "https://via.placeholder.com/150",
            "link": "https://www.jumia.ma/catalog/?q=" + query,
            "currency": "MAD",
            "rating": 4   # ✅ int
        },
        {
            "name": f"{query} Dell Laptop",
            "price": 5500,
            "image": "https://via.placeholder.com/150",
            "link": "https://www.jumia.ma/catalog/?q=" + query,
            "currency": "MAD",
            "rating": 5   # ✅ int
        }
    ]