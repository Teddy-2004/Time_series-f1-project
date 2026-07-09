# Walmart Store Sales — Time Series Pipeline

Group assignment: time-series preprocessing, EDA, modeling, relational + non-relational
database design, CRUD API, and an end-to-end prediction script.

**Dataset:** [Walmart Recruiting - Store Sales Forecasting](https://www.kaggle.com/c/walmart-recruiting-store-sales-forecasting/data) (Kaggle competition)
- `stores.csv` — 45 stores (Type, Size)
- `features.csv` — weekly external variables per store (Temperature, Fuel_Price, CPI, Unemployment, MarkDown1-5, IsHoliday)
- `train.csv` — weekly `Weekly_Sales` per store/department (the forecasting target)

> **Note on data in this repo:** `data/*.csv` here are synthetically generated
> (see `scripts/generate_synthetic_data.py`) with the same schema, column names,
> and realistic missingness patterns as the real Kaggle files, since the
> competition requires an authenticated Kaggle login to download. **To use the
> real data:** join the competition, download `stores.csv`, `features.csv`,
> `train.csv`, and drop them into `data/` with the same filenames — every
> downstream script works unchanged.

## Project structure

```
data/                       raw + processed CSVs, SQLite DB file
models/                     trained model artifact + metadata
reports/                    EDA figures, ERD, experiment table, query results
scripts/
  generate_synthetic_data.py   creates stand-in data matching the real schema
  generate_erd.py              renders the ERD diagram
  predict.py                   Task 4: end-to-end forecast script
src/
  preprocessing.py           Task 1: shared preprocessing pipeline (used by
                              training AND the Task 4 prediction script)
  eda.py                      Task 1: EDA + 5 analytical questions + plots
  train_model.py               Task 1: model training, tuning, experiment table
  database/
    mysql_schema.sql           Task 2: relational schema (3 tables, MySQL DDL)
    setup_mysql_db.py           builds/populates a local SQLite DB from the schema
    mysql_queries.sql            Task 2: 4 example SQL queries
    run_mysql_queries.py         runs the queries, saves results
    setup_mongodb.py             Task 2: MongoDB collection design + 4 queries
  api/
    app_mysql.py                Task 3: CRUD + time-series API for the SQL DB
    app_mongo.py                 Task 3: CRUD + time-series API for MongoDB
```

## How to run everything

```bash
pip install -r requirements.txt   # flask, pymongo, mongomock, scikit-learn, pandas, etc.

# 1) generate data (or drop in the real Kaggle CSVs instead)
python3 scripts/generate_synthetic_data.py

# 2) Task 1: preprocessing + EDA + model training
python3 src/eda.py
python3 src/train_model.py

# 3) Task 2: build both databases + run example queries
python3 src/database/setup_mysql_db.py
python3 src/database/run_mysql_queries.py
python3 src/database/setup_mongodb.py

# 4) Task 3: start the CRUD APIs (separate terminals)
python3 src/api/app_mysql.py     # http://localhost:5001
python3 src/api/app_mongo.py     # http://localhost:5002

# 5) Task 4: run the prediction script (needs the SQL API running)
python3 scripts/predict.py <store_id> <dept_id>
# e.g. python3 scripts/predict.py 1 1
```

## Task summaries

**Task 1 — EDA & Modeling.** `src/eda.py` reports the time range (Feb 2010 –
Oct 2012, weekly), documents missing values (MarkDowns filled with 0 since
NaN means "no promotion running"; CPI/Unemployment forward-filled per store as
slow-moving macro indicators), and answers 5 analytical questions, two of
which use lag features (52-week lag correlation) and moving averages (12-week
rolling mean). `src/train_model.py` compares 3 experiments (Linear Regression
baseline, untuned Random Forest, GridSearchCV-tuned Random Forest) in
`reports/experiment_table.csv`.

**Task 2 — Databases.** Relational schema: `stores` (dimension) →
`store_features` / `sales` (fact tables), FK on `store_id`. MongoDB:
`sales_series` collection, one document per store/dept with an embedded
`readings` array — a genuinely different (denormalized/embedded) design
choice vs. the relational tables. 4 queries run against each DB (see
`reports/sql_query_results.md` and `reports/mongo_query_results.md`).

**Task 3 — CRUD APIs.** Full POST/GET/PUT/DELETE for both databases, plus
the required `latest record` and `date range` endpoints, implemented in Flask
(`src/api/app_mysql.py`, `src/api/app_mongo.py`).

**Task 4 — Prediction script.** `scripts/predict.py` fetches the latest
record from the live SQL API, rebuilds the exact Task-1 feature pipeline,
loads the trained model, and forecasts next week's sales.

## Team contributions

| Member | Component |
|---|---|
| _[Name 1]_ | Task 1 — EDA, analytical questions, visualizations |
| _[Name 2]_ | Task 1 — Feature engineering, model training & tuning |
| _[Name 3]_ | Task 2 — Relational + MongoDB schema design, queries |
| _[Name 4]_ | Task 3 & 4 — CRUD API, prediction script integration |

_(Fill in real names/commits before submitting — the rubric grades individual
GitHub commit history separately.)_
