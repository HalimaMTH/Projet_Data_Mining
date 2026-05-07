from sklearn.cluster import KMeans


def apply_clustering(df):
    # =======================
    # Préparer les données
    # =======================
    X = df[['price_mad']]

    # =========================
    # Appliquer KMeans (3 clusters)
    # =========================
    model = KMeans(n_clusters=3, random_state=42)
    df['cluster'] = model.fit_predict(X)

    # =========================
    # Calculer la moyenne de chaque cluster
    # =========================
    means = df.groupby('cluster')['price_mad'].mean()

    # Trier les clusters du moins cher au plus cher
    means = means.sort_values()

    # =========================
    # Créer un mapping logique
    # =========================
    mapping = {}

    mapping[means.index[0]] = "Cheap"       # le moins cher
    mapping[means.index[1]] = "Medium"      # moyen
    mapping[means.index[2]] = "Expensive"   # le plus cher

    # =========================
    # Appliquer le mapping
    # =========================
    df['cluster'] = df['cluster'].map(mapping)

    return df