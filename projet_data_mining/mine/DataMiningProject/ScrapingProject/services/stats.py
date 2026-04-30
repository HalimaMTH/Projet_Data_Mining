def compute_stats(df):
    return {
        "min": float(df['price_mad'].min()),
        "max": float(df['price_mad'].max()),
        "mean": float(df['price_mad'].mean()),
        "median": float(df['price_mad'].median())
    }