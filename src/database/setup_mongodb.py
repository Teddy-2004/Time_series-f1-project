"""
Task 2 - MongoDB collection design, sample documents, and example queries.
ALIGNED WITH TEAMMATE'S APPROACH: sales are aggregated at STORE level
(summed across departments), so each document represents one store's full
weekly series rather than one store/department pair.

Collection: "sales_series"
  One document per store (45 total), embedding:
    - store-level metadata (denormalized from stores.csv)
    - an array of weekly readings, each combining store-aggregated sales
      with that week's external features (denormalized from features.csv)

NOTE: this sandbox has no real MongoDB server, so we use mongomock (an
in-memory drop-in for pymongo) to actually execute and verify the queries
below. To point this at a real MongoDB Atlas/server instead, replace:
    import mongomock; client = mongomock.MongoClient()
with:
    from pymongo import MongoClient; client = MongoClient("<connection_string>")
No other code changes are needed -- mongomock implements the same API.
"""
import sys
import json
import mongomock
import pandas as pd
from pathlib import Path

# ── resolve project root (two levels up: src/database/ -> root)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from preprocessing import build_dataset  # noqa: E402

client = mongomock.MongoClient()
db = client["walmart_ts"]
collection = db["sales_series"]
collection.delete_many({})

stores = pd.read_csv(ROOT / "data" / "stores.csv")
agg = build_dataset(drop_na_lags=False)  # already store-level aggregated

docs = []
for store, group in agg.groupby("Store"):
    store_row = stores[stores.Store == store].iloc[0]
    readings = []
    for _, r in group.sort_values("Date").iterrows():
        readings.append({
            "date": r["Date"].strftime("%Y-%m-%d"),
            "weekly_sales": round(float(r["Weekly_Sales"]), 2),
            "is_holiday": bool(r["IsHoliday"]),
            "temperature": None if pd.isna(r["Temperature"]) else round(float(r["Temperature"]), 2),
            "fuel_price": None if pd.isna(r["Fuel_Price"]) else round(float(r["Fuel_Price"]), 3),
            "cpi": None if pd.isna(r["CPI"]) else round(float(r["CPI"]), 3),
            "unemployment": None if pd.isna(r["Unemployment"]) else round(float(r["Unemployment"]), 2),
        })
    docs.append({
        "store_id": int(store),
        "store_type": store_row["Type"],
        "store_size": int(store_row["Size"]),
        "readings": readings
    })

collection.insert_many(docs)
print(f"Inserted {collection.count_documents({})} documents into sales_series")

# save one sample document for the report
sample_doc = collection.find_one({"store_id": 1})
sample_doc["readings"] = sample_doc["readings"][:3]  # trim for readability in report
sample_doc.pop("_id", None)
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)
with open(REPORTS / "mongo_sample_document.json", "w") as f:
    json.dump(sample_doc, f, indent=2)
print("Sample document saved to reports/mongo_sample_document.json")

# ------------------------------------------------------------------
# Example queries (4 total)
# ------------------------------------------------------------------
results_md = []

# Query 1: latest reading for a given store (time-series "latest record")
doc = collection.find_one({"store_id": 1})
latest = max(doc["readings"], key=lambda r: r["date"])
results_md.append(("Q1: latest record for store 1",
                    'db.sales_series.find({store_id: 1})  // then take last element of "readings"',
                    latest))

# Query 2: readings within a date range for store 1
in_range = [r for r in doc["readings"] if "2011-01-01" <= r["date"] <= "2011-03-31"]
results_md.append(("Q2: readings in date range for store 1",
                    '''db.sales_series.aggregate([
  { $match: { store_id: 1 } },
  { $project: { readings: { $filter: {
        input: "$readings", as: "r",
        cond: { $and: [
          { $gte: ["$$r.date", "2011-01-01"] },
          { $lte: ["$$r.date", "2011-03-31"] }
        ]}
  }}}}
])''',
                    in_range))

# Query 3: average weekly_sales across all readings, grouped by store_type
pipeline = [
    {"$unwind": "$readings"},
    {"$group": {"_id": "$store_type", "avg_weekly_sales": {"$avg": "$readings.weekly_sales"}}},
    {"$sort": {"avg_weekly_sales": -1}}
]
agg_result = list(collection.aggregate(pipeline))
results_md.append(("Q3: average weekly sales by store type",
                    json.dumps(pipeline, indent=2), agg_result))

# Query 4: stores with store_size > 150000
big_stores = list(collection.find({"store_size": {"$gt": 150000}}, {"store_id": 1, "store_size": 1, "_id": 0}).limit(5))
results_md.append(("Q4: large stores (size > 150,000 sqft)",
                    'db.sales_series.find({ store_size: { $gt: 150000 } }, { store_id: 1, store_size: 1 })',
                    big_stores))

with open(REPORTS / "mongo_query_results.md", "w") as f:
    for title, query, result in results_md:
        print(f"\n--- {title} ---")
        print(result if not isinstance(result, list) else result[:3])
        f.write(f"## {title}\n\n```javascript\n{query}\n```\n\n**Result (sample):**\n```json\n")
        f.write(json.dumps(result if not isinstance(result, list) else result[:3], indent=2, default=str))
        f.write("\n```\n\n")

print("\nSaved results to reports/mongo_query_results.md")
