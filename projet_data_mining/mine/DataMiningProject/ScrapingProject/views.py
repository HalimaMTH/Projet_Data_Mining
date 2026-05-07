from django.shortcuts import render
import pandas as pd

from .services.scraping import scrape_manager
from .services.clustering import apply_clustering
from .services.anomaly import detect_anomalies
from .services.stats import compute_stats
from .models import Product, SearchHistory

CURRENCY_RATES = {"MAD": 1, "USD": 10, "EUR": 11, "GBP": 13}

AVAILABLE_SITES = {
    "jumia":      "Jumia.ma",
    "avito":      "Avito.ma",
    "mytek":      "Mytek.ma",
    "amazon":     "Amazon.fr",
    "aliexpress": "AliExpress",
    "ebay":       "eBay",
}


def home(request):
    try:
        query = request.GET.get("q", "").strip()
        site  = request.GET.get("site", "jumia")
        if site not in AVAILABLE_SITES:
            site = "jumia"

        if not query:
            return render(request, "index.html", {"sites": AVAILABLE_SITES, "site": site})

        data = scrape_manager(query, site)

        if not data:
            return render(request, "index.html", {
                "error": (
                    f"Aucun produit trouvé sur {AVAILABLE_SITES[site]}. "
                    "Vérifiez que Playwright est installé : pip install playwright && playwright install chromium"
                ),
                "query": query, "site": site, "sites": AVAILABLE_SITES,
            })

        df = pd.DataFrame(data)
        df = df[df["price"].notnull()].drop_duplicates(subset=["name"]).reset_index(drop=True)

        def to_mad(row):
            if "price_override_mad" in row and pd.notnull(row.get("price_override_mad")):
                return row["price_override_mad"]
            rate = CURRENCY_RATES.get(str(row.get("currency", "MAD")).upper(), 1)
            return round(row["price"] * rate, 2)

        df["price_mad"] = df.apply(to_mad, axis=1)
        df = df[df["price_mad"] > 0].reset_index(drop=True)

        if df.empty:
            return render(request, "index.html", {
                "error": "Aucun produit avec un prix valide.",
                "query": query, "site": site, "sites": AVAILABLE_SITES,
            })

        if len(df) >= 3:
            df = apply_clustering(df)
            df = detect_anomalies(df)
        else:
            df["cluster"] = "Medium"
            df["anomaly"] = 1

        df["best_price"] = df["price_mad"] == df["price_mad"].min()
        if "site" not in df.columns:
            df["site"] = AVAILABLE_SITES.get(site, site)

        # SAVE TO DATABASE
        # Save search
        SearchHistory.objects.create(
            query=query,
            site=site,
            result_count=len(df)
        )
        
        # Save products
        for _, row in df.iterrows():
            # Convert anomaly to boolean (handles -1, 1, True, False)
            anomaly_value = row.get('anomaly', False)
            is_anomaly = bool(anomaly_value) and anomaly_value != -1
            
            Product.objects.create(
                name=row['name'],
                price=row['price'],
                currency=row.get('currency', 'MAD'),
                price_mad=row['price_mad'],
                rating=row.get('rating'),
                site=site,
                link=row.get('link'),
                image=row.get('image'),
                cluster=row.get('cluster'),
                anomaly=is_anomaly
            )

        return render(request, "index.html", {
            "stats": compute_stats(df),
            "data":  df.to_dict(orient="records"),
            "query": query,
            "site":  site,
            "sites": AVAILABLE_SITES,
            "total": len(df),
        })

    except Exception as e:
        return render(request, "index.html", {
            "error": f"Erreur : {str(e)}",
            "sites": AVAILABLE_SITES,
        })