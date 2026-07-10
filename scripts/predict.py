"""
Task 4 - End-to-end prediction/forecast script.

Workflow (assignment spec):
    API -> fetch time-series data -> convert to DataFrame -> feature
    engineering -> load trained model -> forecast next week's sales
    -> print the prediction as JSON

Data source
-----------
Primary: the Task 3 MongoDB API (port 5002). GET /mongo/readings/<store_id>
returns the store's FULL weekly series including external features
(temperature, fuel_price, cpi, unemployment) -- enough history to build the
lag and moving-average features a time-series model needs.
Fallback: the Task 3 SQL API (port 5001). GET /sql/sales?store_id=&limit=
returns full sales history but no external features, so those are imputed.

NOTE ON TASK 1 (preprocessing.py / train_model.py)
--------------------------------------------------
Task 1's module and saved model are not in the repository yet. This script
is written to prefer them the moment they land, without code changes:
  * feature engineering: if src/preprocessing.py exposes add_lag_features()
    / build_features(), it is imported and used; otherwise the local
    make_features() below (standard lags, moving averages, calendar fields)
    is the stand-in.
  * model: if models/sales_model.joblib (Task 1's artifact) exists it is
    loaded. Otherwise a clearly-labelled BASELINE RandomForest is trained on
    the fetched history and cached at models/baseline_store_<id>.joblib so
    the pipeline is testable end-to-end today. Delete the baseline artifact
    once the real model is committed.

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
sys.path.insert(0, str(ROOT / "src"))               # so Task 1 imports work

MODEL_DIR = ROOT / "models"
TASK1_MODEL = MODEL_DIR / "sales_model.joblib"      # Task 1's expected artifact

MONGO_URL = "http://localhost:5002"
SQL_URL = "http://localhost:5001"

LAGS = [1, 2, 3, 4]
WINDOWS = [4, 8]
EXTERNAL = ["temperature", "fuel_price", "cpi", "unemployment"]
FEATURES = ([f"lag_{k}" for k in LAGS] + [f"ma_{w}" for w in WINDOWS]
            + ["week_of_year", "month", "is_holiday"] + EXTERNAL)


# ------------------------------------------------------------------
# 1) FETCH: API -> DataFrame
# ------------------------------------------------------------------
def fetch_series_mongo(store_id, base=MONGO_URL):
    """Full series incl. external features from the Mongo API (Task 3)."""
    r = requests.get(f"{base}/mongo/readings/{store_id}", timeout=15)
    r.raise_for_status()
    doc = r.json()
    df = pd.DataFrame(doc["readings"])
    df["store_id"] = doc["store_id"]
    return df


def fetch_series_sql(store_id, base=SQL_URL):
    """Full sales history from the SQL API (no external features)."""
    r = requests.get(f"{base}/sql/sales",
                     params={"store_id": store_id, "limit": 100000}, timeout=15)
    r.raise_for_status()
    rows = r.json()
    if not rows:
        raise ValueError(f"SQL API returned no records for store {store_id}")
    df = pd.DataFrame(rows).rename(columns={"record_date": "date"})
    for col in EXTERNAL:                 # SQL sales endpoint has no externals
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
# 2) PREPROCESS: reuse Task 1's pipeline if present, else stand-in
# ------------------------------------------------------------------
def make_features(df):
    """Lag / moving-average / calendar features on a store-level weekly
    series. Mirrors the transformations Task 1's preprocessing is expected
    to provide; replaced automatically once preprocessing.py exists."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["is_holiday"] = df["is_holiday"].astype(int)
    for col in EXTERNAL:                       # carry values across gaps
        df[col] = df[col].ffill().bfill()
        if df[col].isna().all():               # SQL fallback: no externals
            df[col] = 0.0
    for k in LAGS:
        df[f"lag_{k}"] = df["weekly_sales"].shift(k)
    for w in WINDOWS:                          # shift(1): past weeks only
        df[f"ma_{w}"] = df["weekly_sales"].shift(1).rolling(w).mean()
    iso = df["date"].dt.isocalendar()
    df["week_of_year"] = iso.week.astype(int)
    df["month"] = df["date"].dt.month
    return df


def preprocess(df):
    """Prefer Task 1's real preprocessing module when it lands."""
    try:
        import preprocessing as t1                     # src/preprocessing.py
        for fn_name in ("build_features", "add_lag_features"):
            fn = getattr(t1, fn_name, None)
            if callable(fn):
                print(f"Using Task 1 preprocessing.{fn_name}()")
                return fn(df)
        print("preprocessing.py found but no known feature function; "
              "using Task 4 stand-in features")
    except ImportError:
        print("Task 1 preprocessing.py not in repo yet -> "
              "using Task 4 stand-in feature engineering")
    return make_features(df)


def next_week_feature_row(df):
    """Feature vector for the week after the last observed one."""
    hist = df.sort_values("date")
    s = hist["weekly_sales"]
    next_date = hist["date"].iloc[-1] + timedelta(days=7)
    row = {f"lag_{k}": float(s.iloc[-k]) for k in LAGS}
    row.update({f"ma_{w}": float(s.iloc[-w:].mean()) for w in WINDOWS})
    row["week_of_year"] = int(next_date.isocalendar()[1])
    row["month"] = int(next_date.month)
    row["is_holiday"] = 0                      # unknown for future week
    for col in EXTERNAL:                       # carry last known value
        row[col] = float(hist[col].iloc[-1])
    return pd.DataFrame([row])[FEATURES], next_date


# ------------------------------------------------------------------
# 3) MODEL: load Task 1's artifact, else train a labelled baseline
# ------------------------------------------------------------------
def load_or_train_model(feat_df, store_id):
    if TASK1_MODEL.exists():
        print(f"Loaded trained model: {TASK1_MODEL.relative_to(ROOT)}")
        return joblib.load(TASK1_MODEL)

    baseline_path = MODEL_DIR / f"baseline_store_{store_id}.joblib"
    if baseline_path.exists():
        print(f"Loaded cached BASELINE model: {baseline_path.relative_to(ROOT)}")
        return joblib.load(baseline_path)

    print("WARNING: no Task 1 model artifact (models/sales_model.joblib) "
          "in repo -> training a BASELINE RandomForest on fetched history")
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error

    train = feat_df.dropna(subset=FEATURES + ["weekly_sales"])
    X, y = train[FEATURES], train["weekly_sales"]
    split = int(len(train) * 0.8)              # time-ordered holdout
    model = RandomForestRegressor(n_estimators=300, random_state=42)
    model.fit(X.iloc[:split], y.iloc[:split])
    mae = mean_absolute_error(y.iloc[split:], model.predict(X.iloc[split:]))
    print(f"  baseline holdout MAE ({len(train) - split} weeks): {mae:,.2f}")
    model.fit(X, y)                            # refit on all history
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(model, baseline_path)
    print(f"  cached baseline at {baseline_path.relative_to(ROOT)}")
    return model


# ------------------------------------------------------------------
# 4) PREDICT
# ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Task 4: forecast next week's "
                                 "sales for a store via the Task 3 API")
    ap.add_argument("--store-id", type=int, default=1)
    ap.add_argument("--api", choices=["auto", "mongo", "sql"], default="auto")
    args = ap.parse_args()

    raw, source = fetch_series(args.store_id, args.api)          # 1) fetch
    feat = preprocess(raw)                                       # 2) features
    model = load_or_train_model(feat, args.store_id)             # 3) model
    X_next, next_date = next_week_feature_row(feat)
    pred = float(model.predict(X_next)[0])                       # 4) forecast

    result = {
        "store_id": args.store_id,
        "history_weeks": int(len(raw)),
        "last_observed_date": str(feat["date"].max().date()),
        "last_observed_weekly_sales": round(float(
            feat.sort_values("date")["weekly_sales"].iloc[-1]), 2),
        "forecast_date": str(next_date.date()),
        "predicted_weekly_sales": round(pred, 2),
        "model": type(model).__name__,
        "model_source": ("task1_artifact" if TASK1_MODEL.exists()
                         else "baseline_stand_in"),
        "data_source": f"{source}_api",
    }
    print("\n" + json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
