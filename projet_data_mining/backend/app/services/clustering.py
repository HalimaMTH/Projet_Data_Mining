from sklearn.cluster import KMeans

def apply_clustering(df):
    X = df[['price_mad']]

    model = KMeans(n_clusters=3, random_state=42)
    df['cluster'] = model.fit_predict(X)

    return df