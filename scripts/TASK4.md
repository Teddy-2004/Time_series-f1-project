# Task 4 — Prediction / Forecast Script

`scripts/predict.py` is the final integration step: it consumes the Task 3
API, rebuilds model features from the returned history, loads the trained
model, and prints a one-week-ahead sales forecast for a store.

## Workflow

```
Task 3 API ──> fetch full weekly series ──> pandas DataFrame
          ──> feature engineering (lags 1–4, moving averages 4/8,
              week-of-year, month, holiday flag, external features)
          ──> load trained model (joblib)
          ──> predict next week's Weekly_Sales ──> print JSON
```

## Data source — why the Mongo API is the default

Both Task 3 services return **full history**, not just the latest record, so
lag/moving-average features can be built client-side:

| Source | Endpoint used | Externals (temp, fuel, CPI, unemp.)? |
|---|---|---|
| Mongo API `:5002` (default) | `GET /mongo/readings/<store_id>` | ✅ included per reading |
| SQL API `:5001` (fallback) | `GET /sql/sales?store_id=&limit=` | ❌ sales only → imputed as 0 |

`--api auto` (default) tries Mongo first, then SQL.

## Model resolution order

1. `models/sales_model.joblib` — **Task 1's real artifact**, loaded as-is the
   moment it is committed.
2. `models/baseline_store_<id>.joblib` — cached baseline from a previous run.
3. Neither exists → trains a clearly-labelled **baseline RandomForest** on the
   fetched history (time-ordered 80/20 holdout MAE printed), caches it, and
   proceeds. This keeps Task 4 testable before Task 1 lands.

The same applies to preprocessing: if `src/preprocessing.py` exposes
`build_features()` / `add_lag_features()`, it is imported and used;
otherwise `make_features()` in `predict.py` is the stand-in.

## Run

```bash
pip install -r requirements.txt

# terminal 1 — start either Task 3 service
python3 src/api/app_mongo.py            # port 5002 (preferred)
# or: python3 src/api/app_mysql.py      # port 5001

# terminal 2 — forecast
python3 scripts/predict.py --store-id 1
python3 scripts/predict.py --store-id 20 --api sql
```

Example output:

```json
{
  "store_id": 1,
  "history_weeks": 143,
  "last_observed_date": "2012-10-26",
  "last_observed_weekly_sales": 376004.77,
  "forecast_date": "2012-11-02",
  "predicted_weekly_sales": 388037.5,
  "model": "RandomForestRegressor",
  "model_source": "baseline_stand_in",
  "data_source": "mongo_api"
}
```

## Open items for the team (Task 1 hand-off)

- `src/preprocessing.py`, `src/train_model.py`, `src/eda.py` and
  `reports/experiment_table.csv` are referenced by the README but not yet
  committed. When they land, commit the trained model as
  `models/sales_model.joblib` — `predict.py` will pick it up automatically
  (`"model_source": "task1_artifact"`).
- Task 1's model must expose the feature contract it was trained with; if it
  differs from the stand-in feature list in `predict.py`, update `FEATURES`
  there (single source of truth at the top of the file).
- Future-week external features (temperature, fuel price, CPI, unemployment)
  are unknown at forecast time; the script carries the last observed values
  forward and treats the future week as a non-holiday. Flag via
  `is_holiday` handling if the team wants holiday-aware forecasts.
