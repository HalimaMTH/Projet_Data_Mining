from django.shortcuts import render
import pandas as pd
import random

from .services.clustering import apply_clustering
from .services.anomaly import detect_anomalies
from .services.stats import compute_stats


def home(request):
    query = request.GET.get("q")

    # =========================
    # simulate scraping
    # =========================
    if query:
        data = [
            {"name": f"{query} - HP Version", "price": random.randint(4000, 6000), "currency": "MAD", "link": "https://jumia.ma"},
            {"name": f"{query} - Dell Version", "price": random.randint(4500, 6500), "currency": "MAD", "link": "https://avito.ma"},
            {"name": f"{query} - Asus Version", "price": random.randint(4200, 6200), "currency": "MAD", "link": "https://amazon.com"},
        ]
    else:
        data = []

    if not data:
        return render(request, "index.html")

    df = pd.DataFrame(data)
    df["price_mad"] = df["price"]

    df = apply_clustering(df)
    df = detect_anomalies(df)

    best_price = df["price_mad"].min()
    df["best_price"] = df["price_mad"] == best_price

    stats = compute_stats(df)

    return render(request, "index.html", {
        "stats": stats,
        "data": df.to_dict(orient='records'),
        "query": query
    })