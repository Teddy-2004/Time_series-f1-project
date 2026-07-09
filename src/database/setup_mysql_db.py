"""
Sets up and populates the relational database at STORE-LEVEL granularity
(sales summed across departments), aligned with the teammate's approach.

NOTE ON MySQL VS SQLite: this sandbox has no MySQL server process available,
so we execute an SQLite-compatible translation of the schema to actually run
and verify queries end-to-end. The authoritative schema is mysql_schema.sql
(real MySQL DDL). To point this at a real MySQL server, swap the sqlite3
connection below for mysql.connector -- no other code changes needed.
"""
import sys
import sqlite3
import pandas as pd
from pathlib import Path

# ── resolve project root (two levels up from this file: src/database/ -> root)
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "walmart_ts.db"

SQLITE_SCHEMA = """
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS store_features;
DROP TABLE IF EXISTS stores;

CREATE TABLE stores (
    store_id     INTEGER PRIMARY KEY,
    store_type   TEXT NOT NULL,
    size_sqft    INTEGER NOT NULL
);

CREATE TABLE store_features (
    feature_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id      INTEGER NOT NULL,
    record_date   TEXT NOT NULL,
    temperature   REAL,
    fuel_price    REAL,
    markdown1     REAL,
    markdown2     REAL,
    markdown3     REAL,
    markdown4     REAL,
    markdown5     REAL,
    cpi           REAL,
    unemployment  REAL,
    is_holiday    INTEGER DEFAULT 0,
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    UNIQUE (store_id, record_date)
);
CREATE INDEX idx_features_date ON store_features(record_date);

CREATE TABLE sales (
    sale_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id      INTEGER NOT NULL,
    record_date   TEXT NOT NULL,
    weekly_sales  REAL NOT NULL,
    is_holiday    INTEGER DEFAULT 0,
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    UNIQUE (store_id, record_date)
);
CREATE INDEX idx_sales_date ON sales(record_date);
CREATE INDEX idx_sales_store_date ON sales(store_id, record_date);
"""


def build_db():
    sys.path.insert(0, str(ROOT / "src"))
    from preprocessing import load_raw, merge_datasets, aggregate_to_store_week, handle_missing_values

    stores_df = pd.read_csv(ROOT / "data" / "stores.csv")
    stores, features, train = load_raw()
    merged = merge_datasets(stores, features, train)
    weekly = aggregate_to_store_week(merged)
    weekly = handle_missing_values(weekly)

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SQLITE_SCHEMA)

    stores_df.rename(columns={"Store": "store_id", "Type": "store_type", "Size": "size_sqft"}) \
        .to_sql("stores", conn, if_exists="append", index=False)

    feat = weekly.rename(columns={
        "Store": "store_id", "Date": "record_date", "Temperature": "temperature",
        "Fuel_Price": "fuel_price", "MarkDown1": "markdown1", "MarkDown2": "markdown2",
        "MarkDown3": "markdown3", "MarkDown4": "markdown4", "MarkDown5": "markdown5",
        "CPI": "cpi", "Unemployment": "unemployment", "IsHoliday": "is_holiday"
    })[["store_id", "record_date", "temperature", "fuel_price", "markdown1", "markdown2",
        "markdown3", "markdown4", "markdown5", "cpi", "unemployment", "is_holiday"]].copy()
    feat["is_holiday"] = feat["is_holiday"].astype(int)
    feat["record_date"] = feat["record_date"].astype(str)
    feat.to_sql("store_features", conn, if_exists="append", index=False)

    sal = weekly.rename(columns={
        "Store": "store_id", "Date": "record_date", "Weekly_Sales": "weekly_sales",
        "IsHoliday": "is_holiday"
    })[["store_id", "record_date", "weekly_sales", "is_holiday"]].copy()
    sal["is_holiday"] = sal["is_holiday"].astype(int)
    sal["record_date"] = sal["record_date"].astype(str)
    sal.to_sql("sales", conn, if_exists="append", index=False)

    conn.commit()
    conn.close()
    print(f"Database built at {DB_PATH}")
    print(f"  stores: {len(stores_df)} rows | store_features: {len(feat)} rows | sales: {len(sal)} rows")


if __name__ == "__main__":
    build_db()
