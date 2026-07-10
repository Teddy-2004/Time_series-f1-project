from pathlib import Path
import pandas as pd

# data folder sits one level up from src/, resolved from this file's location
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

markdown_cols = ['MarkDown1', 'MarkDown2', 'MarkDown3', 'MarkDown4', 'MarkDown5']

# columns used to train the model, in this order
FEATURES = [
    'Temperature', 'Fuel_Price', 'CPI', 'Unemployment', 'IsHoliday',
    'MarkDown1', 'MarkDown2', 'MarkDown3', 'MarkDown4', 'MarkDown5',
    'sales_lag_1', 'sales_lag_52', 'sales_ma4',
]


def load_raw(data_dir=DATA_DIR):
    stores = pd.read_csv(data_dir / "stores.csv")
    features = pd.read_csv(data_dir / "features.csv")
    train = pd.read_csv(data_dir / "train.csv")
    features['Date'] = pd.to_datetime(features['Date'])
    train['Date'] = pd.to_datetime(train['Date'])
    return stores, features, train


def merge_datasets(stores, features, train):
    # drop the duplicate IsHoliday, then attach each week's variables to the sales rows
    merged = train.merge(features.drop(columns='IsHoliday'), on=['Store', 'Date'], how='left')
    merged = merged.merge(stores, on='Store', how='left')
    return merged


def aggregate_to_store_week(merged):
    # sum department sales into a store total; the rest is the same across departments
    weekly = merged.groupby(['Store', 'Date']).agg({
        'Weekly_Sales': 'sum',
        'Temperature': 'first',
        'Fuel_Price': 'first',
        'MarkDown1': 'first',
        'MarkDown2': 'first',
        'MarkDown3': 'first',
        'MarkDown4': 'first',
        'MarkDown5': 'first',
        'CPI': 'first',
        'Unemployment': 'first',
        'IsHoliday': 'first',
    }).reset_index()
    return weekly


def handle_missing_values(weekly):
    weekly = weekly.copy()
    # empty markdown means no promotion that week
    weekly[markdown_cols] = weekly[markdown_cols].fillna(0)
    return weekly


def make_features(df):
    df = df.copy()
    df = df.sort_values('Date')
    df['sales_lag_1'] = df['Weekly_Sales'].shift(1)
    df['sales_lag_52'] = df['Weekly_Sales'].shift(52)
    df['sales_ma4'] = df['Weekly_Sales'].rolling(4).mean().shift(1)
    return df


def build_dataset(data_dir=DATA_DIR, drop_na_lags=False):
    stores, features, train = load_raw(data_dir)
    merged = merge_datasets(stores, features, train)
    weekly = aggregate_to_store_week(merged)
    weekly = handle_missing_values(weekly)

    # features are built per store so lags stay within one store
    weekly = pd.concat([make_features(group) for _, group in weekly.groupby('Store')],
                       ignore_index=True)

    if drop_na_lags:
        weekly = weekly.dropna(subset=['sales_lag_1', 'sales_lag_52', 'sales_ma4'])
    return weekly