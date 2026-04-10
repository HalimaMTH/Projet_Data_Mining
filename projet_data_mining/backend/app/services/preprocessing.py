import pandas as pd

def preprocess_pipeline(path):
    df = pd.read_csv(path)

    df = df.drop_duplicates()
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df = df.dropna(subset=['price'])

    df['currency'] = df['currency'].fillna('MAD')

    rates = {'MAD': 1, 'USD': 10, 'EUR': 11}
    df['price_mad'] = df.apply(lambda x: x['price'] * rates[x['currency']], axis=1)

    return df
    