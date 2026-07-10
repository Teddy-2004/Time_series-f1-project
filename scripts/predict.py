"""
Task 4 - End-to-end prediction/forecast script.

Workflow (assignment spec):
    API -> fetch time-series data -> convert to DataFrame -> Task 1
    preprocessing (src/preprocessing.py) -> load Task 1's trained model
    -> forecast next week's sales -> print the prediction as JSON

Data source
-----------
Primary: the Task 3 MongoDB API (port 5002). GET /mongo/readings/<store_id>
returns the store's FULL weekly series including external features -- enough
history to build Task 1's lag features (sales_lag_1, sales_lag_52, sales_ma4).
Fallback: the Task 3 SQL API (port 5001), sales history only (externals
imputed).

Model
-----
Task 1's artifact (Task1/model/store<id>_model.pkl) is a dict:
    {"model": Pipeline(StandardScaler -> Ridge), "features": [13 columns]}
Feature engineering is NOT duplicated here -- preprocessing.make_features()
and preprocessing.FEATURES are imported from Task 1's module.

Known limitation (documented, not assumed away): the Task 3 API does not
expose MarkDown1-5. Task 1's own rule (handle_missing_values) treats a
missing markdown as "no promotion" = 0, so the same rule is applied here.

Run:
    python3 src/api/app_mongo.py            # terminal 1 (or app_mysql.py)
    python3 scripts/predict.py --store-id 1 # terminal 2
"""
import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import requests

# ── project-root resolution, same pattern as the Task 2/3 scripts
ROOT = Path(__file__).resolve().parents[1]          # scripts/ -> project root
sys.path.insert(0, str(ROOT / "src"))

import preprocessing                                 # Task 1's module

MODEL_DIR = ROOT / "Task1" / "model"

MONGO_URL = "http://localhost:5002"
SQL_URL = "http://localhost:5001"

# API field names (lowercase) -> Task 1 / CSV column names
COLMAP = {
    "date": "Date", "weekly_sales": "Weekly_Sales", "is_holiday": "IsHoliday",
    "temperature": "Temperature", "fuel_price": "Fuel_Price",
    "cpi": "CPI", "unemployment": "Unemployment",
}
EXTERNAL = ["Temperature", "Fuel_Price", "CPI", "Unemployment"]
MARKDOWNS = preprocessing.markdown_cols              # MarkDown1..5
FEATURES = preprocessing.FEATURES                    # Task 1's 13 features


# ------------------------------------------------------------------
# 1) FETCH: API -> DataFrame
# ------------------------------------------------------------------
def fetch_series_mongo(store_id, base=MONGO_URL):
    """Full series incl. external features from the Mongo API (Task 3)."""
    r = requests.get(f"{base}/mongo/readings/{store_id}", timeout=15)
    r.raise_for_status()
    return pd.DataFrame(r.json()["readings"])


def fetch_series_sql(store_id, base=SQL_URL):
    """Full sales history from the SQL API (no external features)."""
    r = requests.get(f"{base}/sql/sales",
                     params={"store_id": store_id, "limit": 100000}, timeout=15)
    r.raise_for_status()
    rows = r.json()
    if not rows:
        raise ValueError(f"SQL API returned no records for store {store_id}")
    df = pd.DataFrame(rows).rename(columns={"record_date": "date"})
    for col in ("temperature", "fuel_price", "cpi", "unemployment"):
        df[col] = np.nan
    return df


def fetch_series(store_id, source="auto"):
    """Try the Mongo API first (richer payload), fall back to SQL."""
    attempts = {"mongo": [fetch_series_mongo], "sql": [fetch_series_sql],
                "auto": [fetch_series_mongo, fetch_series_sql]}[source]
    last_err = None
    for fn in attempts:
        try:
            df = fn(store_id)
            used = "mongo" if fn is fetch_series_mongo else "sql"
            print(f"Fetched {len(df)} weekly records for store {store_id} "
                  f"via the {used.upper()} API")
            return df, used
        except (requests.ConnectionError, requests.Timeout) as e:
            last_err = e
    raise SystemExit(
        f"Could not reach any API ({last_err}).\n"
        "Start one first:  python3 src/api/app_mongo.py   (port 5002)\n"
        "             or:  python3 src/api/app_mysql.py   (port 5001)")


# ------------------------------------------------------------------
# 2) PREPROCESS: reuse Task 1's pipeline (src/preprocessing.py)
# ------------------------------------------------------------------
def to_task1_frame(df):
    """Rename API JSON fields to the column names Task 1's functions expect,
    and apply the same missing-value rules as preprocessing.py."""
    df = df.rename(columns=COLMAP).copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df["IsHoliday"] = df["IsHoliday"].astype(int)
    for col in EXTERNAL:
        df[col] = df[col].ffill().bfill()
        if df[col].isna().all():           # SQL fallback has no externals
            df[col] = 0.0
    for col in MARKDOWNS:                  # not exposed by the Task 3 API;
        df[col] = 0.0                      # Task 1 rule: missing = 0
    return df.sort_values("Date").reset_index(drop=True)


def next_week_feature_row(feat):
    """Task 1's feature vector for the week after the last observed one."""
    hist = feat.sort_values("Date")
    if len(hist) < 52:
        raise SystemExit(f"Need >= 52 weeks of history for sales_lag_52, "
                         f"got {len(hist)}")
    s = hist["Weekly_Sales"]
    next_date = hist["Date"].iloc[-1] + timedelta(days=7)
    row = {c: float(hist[c].iloc[-1]) for c in EXTERNAL}   # carry forward
    row.update({c: 0.0 for c in MARKDOWNS})
    row["IsHoliday"] = 0                                   # unknown future
    row["sales_lag_1"] = float(s.iloc[-1])
    row["sales_lag_52"] = float(s.iloc[-52])
    row["sales_ma4"] = float(s.iloc[-4:].mean())
    return pd.DataFrame([row])[FEATURES], next_date


# ------------------------------------------------------------------
# 3) MODEL: load Task 1's saved artifact
# ------------------------------------------------------------------
def load_model(store_id):
    """Task 1 saves {'model': Pipeline, 'features': [...]} per store."""
    path = MODEL_DIR / f"store{store_id}_model.pkl"
    note = ""
    if not path.exists():
        path = MODEL_DIR / "store1_model.pkl"
        note = (" (trained on store 1 -- results for other stores are "
                "indicative only)")
        if not path.exists():
            raise SystemExit(f"No Task 1 model artifact found in {MODEL_DIR}")
    bundle = joblib.load(path)
    model, feats = bundle["model"], bundle["features"]
    assert feats == FEATURES, (
        "Model feature list differs from preprocessing.FEATURES -- "
        "retrain or update src/preprocessing.py")
    print(f"Loaded Task 1 model: {path.relative_to(ROOT)}{note}")
    return model, str(path.relative_to(ROOT)) + note


# ------------------------------------------------------------------
# 4) PREDICT
# ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Task 4: forecast next week's "
                                 "sales for a store via the Task 3 API")
    ap.add_argument("--store-id", type=int, default=1)
    ap.add_argument("--api", choices=["auto", "mongo", "sql"], default="auto")
    args = ap.parse_args()

    raw, source = fetch_series(args.store_id, args.api)      # 1) fetch
    frame = to_task1_frame(raw)                              # 2) preprocess
    feat = preprocessing.make_features(frame)                #    (Task 1 code)
    model, model_src = load_model(args.store_id)             # 3) load model
    X_next, next_date = next_week_feature_row(feat)
    pred = float(model.predict(X_next)[0])                   # 4) forecast

    result = {
        "store_id": args.store_id,
        "history_weeks": int(len(raw)),
        "last_observed_date": str(feat["Date"].max().date()),
        "last_observed_weekly_sales": round(float(
            feat.sort_values("Date")["Weekly_Sales"].iloc[-1]), 2),
        "forecast_date": str(next_date.date()),
        "predicted_weekly_sales": round(pred, 2),
        "model": "StandardScaler + Ridge (Task 1 pipeline)",
        "model_source": model_src,
        "data_source": f"{source}_api",
    }
    print("\n" + json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
