from sklearn.ensemble import IsolationForest

def detect_anomalies(df):
    model = IsolationForest(contamination=0.2, random_state=42)
    df['anomaly'] = model.fit_predict(df[['price_mad']])
    return df