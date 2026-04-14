from django.shortcuts import render
import pandas as pd

from .services.scraping import scrape_products
from .services.clustering import apply_clustering
from .services.anomaly import detect_anomalies
from .services.stats import compute_stats


def home(request):
    try:
        # =========================
        # Récupérer la requête utilisateur
        # =========================
        query = request.GET.get("q")

        # =========================
        # Scraping
        # =========================
        if query:
            data = scrape_products(query)
        else:
            data = []

        # =========================
        # Si aucune donnée retournée
        # =========================
        if not data:
            return render(request, "index.html", {
                "error": "Aucun produit trouvé"
            })

        # =========================
        # Transformer en DataFrame
        # =========================
        df = pd.DataFrame(data)

        # =========================
        # Nettoyage sécurisé (IMPORTANT)
        # =========================

        # Supprimer les lignes sans prix
        df = df[df["price"].notnull()]

        # Supprimer les doublons
        df = df.drop_duplicates(subset=["name"])

        # Reset index
        df = df.reset_index(drop=True)

        # ⚠️ Vérifier si DataFrame est vide
        if df.empty:
            return render(request, "index.html", {
                "error": "Aucune donnée exploitable"
            })

        # =========================
        # Conversion en MAD
        # =========================
        df["price_mad"] = df["price"]

        # =========================
        # Clustering (avec protection)
        # =========================
        if len(df) >= 3:
            df = apply_clustering(df)
        else:
            # Si pas assez de données → cluster simple
            df["cluster"] = "Medium"

        # =========================
        # Détection anomalies
        # =========================
        if len(df) >= 3:
            df = detect_anomalies(df)
        else:
            df["anomaly"] = 1  # Normal

        # =========================
        # Best price
        # =========================
        best_price = df["price_mad"].min()
        df["best_price"] = df["price_mad"] == best_price

        # =========================
        # Stats
        # =========================
        stats = compute_stats(df)

        # =========================
        # Return HTML
        # =========================
        return render(request, "index.html", {
            "stats": stats,
            "data": df.to_dict(orient='records'),
            "query": query
        })

    except Exception as e:
        return render(request, "index.html", {
            "error": str(e)
        })