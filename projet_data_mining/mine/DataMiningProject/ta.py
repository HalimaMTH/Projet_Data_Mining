import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DataMiningProject.settings")
django.setup()

import requests, re, json

# ── Avito : voir le contenu réel de la page
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.avito.ma/",
})
r = session.get("https://www.avito.ma/fr/maroc?query=iphone+14", timeout=15)
html = r.text

# Chercher __NEXT_DATA__
next_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
print("=== AVITO ===")
print("Status:", r.status_code)
print("__NEXT_DATA__ trouvé:", bool(next_match))
if next_match:
    try:
        data = json.loads(next_match.group(1))
        props = data.get("props", {}).get("pageProps", {})
        print("Clés pageProps:", list(props.keys())[:10])
    except:
        print("JSON parse error")

# Classes dans le HTML (pour trouver les bons sélecteurs)
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "html.parser")
# Chercher les prix MAD/DH
prix = re.findall(r'[\d\s]+(?:DH|MAD)', html[:50000])
print("Prix trouvés:", prix[:5])
# Chercher balises articles/listings
arts = soup.find_all(["article", "li"], limit=5)
print("Balises article/li:", [(t.name, list(t.attrs.keys())[:3]) for t in arts])

print()

# ── Mytek
print("=== MYTEK ===")
s2 = requests.Session()
s2.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
})
r2 = s2.get("https://www.mytek.ma/catalogsearch/result/?q=iphone+14", timeout=15)
print("Status:", r2.status_code)
print("Taille:", len(r2.text))
soup2 = BeautifulSoup(r2.text, "html.parser")
# Chercher produits
items = soup2.select(".product-item, li.product-item, .product-item-info")
print("product-item trouvés:", len(items))
prix2 = re.findall(r'[\d\s.,]+\s*(?:DT|DH|MAD|TND)', r2.text[:30000])
print("Prix trouvés:", prix2[:5])
# Classes fréquentes
all_classes = []
for tag in soup2.find_all(True, limit=200):
    all_classes.extend(tag.get("class", []))
from collections import Counter
print("Classes fréquentes:", Counter(all_classes).most_common(15))