from django.shortcuts import render
import pandas as pd

from .services.scraping import scrape_products
from .services.clustering import apply_clustering
from .services.anomaly import detect_anomalies
from .services.stats import compute_stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
import base64

def generate_chart(df, chart_type):
    buffer = io.BytesIO()

    plt.figure(figsize=(7, 4))

    if chart_type == "histogram":
        plt.hist(df["price_mad"], bins=10)
        plt.title("Distribution des prix")
        plt.xlabel("Prix en MAD")
        plt.ylabel("Nombre de produits")

    elif chart_type == "clusters":
        df["cluster"].value_counts().plot(kind="bar")
        plt.title("Répartition des clusters")
        plt.xlabel("Cluster")
        plt.ylabel("Nombre de produits")

    elif chart_type == "boxplot":
        plt.boxplot(df["price_mad"])
        plt.title("Détection visuelle des anomalies")
        plt.ylabel("Prix en MAD")

    plt.tight_layout()
    plt.savefig(buffer, format="png")
    buffer.seek(0)

    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()
    plt.close()

    return image_base64


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
          source = request.GET.get("source", "jumia")
          data = scrape_products(query, source)
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

        histogram_chart = generate_chart(df, "histogram")
        cluster_chart = generate_chart(df, "clusters")
        boxplot_chart = generate_chart(df, "boxplot")

        # Nombre total de produits
        total_products = len(df)

        # Meilleur produit
        best_product = df[df["best_price"] == True].iloc[0].to_dict()

        # Top 5 produits les moins chers
        top_cheap_products = df.sort_values(by="price_mad").head(5).to_dict(orient="records")

        # =========================
        # Return HTML
        # =========================
        return render(request, "index.html", {
            "stats": stats,
            "data": df.to_dict(orient='records'),
            "query": query,
            "histogram_chart": histogram_chart,
            "cluster_chart": cluster_chart,
            "boxplot_chart": boxplot_chart,
            "total_products": total_products,
            "best_product": best_product,
            "top_cheap_products": top_cheap_products,
        })

    except Exception as e:
        return render(request, "index.html", {
            "error": str(e)
        })