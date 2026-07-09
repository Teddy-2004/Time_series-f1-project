# Walmart Store Sales Forecasting — Time Series Pipeline

A group assignment implementing a full time-series pipeline on the
[Walmart Store Sales Forecasting](https://www.kaggle.com/c/walmart-recruiting-store-sales-forecasting)
dataset from Kaggle.

## Dataset

| Property | Detail |
|---|---|
| Source | Kaggle — Walmart Store Sales Forecasting |
| Time range | 2010-02-05 → 2012-10-26 |
| Granularity | Weekly (Friday cut-off) |
| Stores | 45 stores, 3 types (A / B / C) |
| Target variable | `Weekly_Sales` (aggregated at store level) |
| Key features | Temperature, Fuel Price, CPI, Unemployment, MarkDowns 1-5, IsHoliday |

---

## Repository Structure

```
walmart-ts-project/
├── data/
│   ├── stores.csv          # Store metadata (45 stores)
│   ├── features.csv        # Weekly external variables
│   ├── train.csv           # Weekly sales per store/department
│   └── walmart_ts.db       # Pre-built SQLite database (Task 2)
├── src/
│   ├── preprocessing.py    # Data loading, merging, feature engineering
│   ├── eda.py              # Exploratory data analysis (Task 1)
│   ├── train_model.py      # Model training & hyperparameter tuning (Task 1)
│   ├── database/
│   │   ├── mysql_schema.sql        # MySQL DDL — 3-table relational schema
│   │   ├── mysql_queries.sql       # 4 analytical SQL queries
│   │   ├── setup_mysql_db.py       # Builds the SQLite database from CSVs
│   │   ├── run_mysql_queries.py    # Runs queries → reports/sql_query_results.md
│   │   ├── mongodb_design.md       # MongoDB collection design & rationale
│   │   └── setup_mongodb.py        # Populates mongomock + runs 4 queries
│   └── api/
│       ├── app_mysql.py    # Flask CRUD endpoints for SQL (Task 3)
│       └── app_mongo.py    # Flask CRUD endpoints for MongoDB (Task 3)
├── scripts/
│   ├── generate_erd.py     # Generates the ERD diagram (Task 2)
│   └── predict.py          # End-to-end forecast script (Task 4)
├── reports/
│   ├── figures/
│   │   └── erd_diagram.png         # Auto-generated ERD
│   ├── sql_query_results.md        # SQL query outputs
│   ├── mongo_query_results.md      # MongoDB query outputs
│   ├── mongo_sample_document.json  # Sample MongoDB document
│   └── experiment_table.csv        # Model experiment results
├── requirements.txt
└── README.md
```

---

## Tasks Overview

### Task 1 — Time-Series Preprocessing & EDA
Performed by team members focusing on exploration, feature engineering, and modelling.

- Exploratory analysis: time range, granularity, missing values, statistical distributions
- 5+ analytical questions answered with visualisations (trends, lag effects, moving averages)
- ML model trained with hyperparameter tuning and experiment table

### Task 2 — Database Design (SQL & MongoDB) *(this contributor)*

#### Relational Database (MySQL / SQLite)
- **3-table schema**: `stores` (dimension) → `store_features` (time-varying context) → `sales` (fact/target)
- **ERD diagram**: see `reports/figures/erd_diagram.png`
- **SQL schema**: `src/database/mysql_schema.sql`
- **4 queries**: latest record, date range, average sales by store type, total sales vs temperature

#### MongoDB
- **Collection design**: `sales_series` — one document per store, embedded `readings` array (bucket-per-entity pattern ideal for time-series queries)
- **Sample document**: `reports/mongo_sample_document.json`
- **4 queries**: latest reading, date-range filter, average sales by store type, large-store lookup

### Task 3 — CRUD API Endpoints
Flask REST API for both databases (POST, GET, PUT, DELETE + latest-record and date-range endpoints).

### Task 4 — Prediction Script
End-to-end script that fetches data from the API, preprocesses it, loads the trained model, and produces a forecast.

---

## Reproducing Task 2

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Re)build the SQLite database from raw CSVs
python src/database/setup_mysql_db.py

# 3. Run SQL queries → reports/sql_query_results.md
python src/database/run_mysql_queries.py

# 4. Run MongoDB setup & queries → reports/mongo_query_results.md
python src/database/setup_mongodb.py

# 5. Regenerate the ERD diagram
python scripts/generate_erd.py
```

---

## Team Contributions

| Member | Task |
|---|---|
| **Principie Cyubahiro** | **Task 1: Time-series Preprocessing and Exploratory Analysis** |
| **Tedla Tesfaye Godebo** | **Task 2 — Database Design (SQL & MongoDB)** |
| **Mahlet Assefa Tilahun**| **Task 3: Create Endpoints for CRUD and Time-Series Queries** |
| **Tapiwanashe Marufu**| **Task 4: Create a Prediction/Forecast Script** |

---

## Requirements

See [`requirements.txt`](requirements.txt). Key dependencies: `pandas`, `numpy`, `scikit-learn`, `flask`, `pymongo`, `mongomock`, `matplotlib`, `joblib`.