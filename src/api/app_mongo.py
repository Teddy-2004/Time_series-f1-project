"""
Task 3 - CRUD + time-series API for the MongoDB database.

Endpoints
---------
GET    /                                              health check + endpoint list
POST   /mongo/readings                                append a reading to a store's series
GET    /mongo/readings/<store_id>                     read the full series
PUT    /mongo/readings/<store_id>/<date>              update one dated reading
DELETE /mongo/readings/<store_id>/<date>              delete one dated reading
GET    /mongo/readings/<store_id>/latest              latest reading            (time-series)
GET    /mongo/readings/<store_id>/range?start=&end=   readings in a date range   (time-series)

Run:
    python3 src/api/app_mongo.py        # serves on http://localhost:5002
"""
from pathlib import Path
from datetime import datetime
import sqlite3
import mongomock
from flask import Flask, request, jsonify

# same project-root resolution as the Task 2 setup scripts
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = str(ROOT / "data" / "walmart_ts.db")

app = Flask(__name__)
client = mongomock.MongoClient()
collection = client["walmart_ts"]["sales_series"]    # same db + collection as Task 2


def valid_date(s):
    try:
        datetime.strptime(str(s), "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def strip_id(doc):
    if doc:
        doc.pop("_id", None)
    return doc


def _round(v, n):
    return None if v is None else round(float(v), n)


def build_documents():
    """One document per store (metadata + embedded readings array), built from
    the Task 2 SQLite DB. Mirrors the document shape in setup_mongodb.py."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    stores = conn.execute(
        "SELECT store_id, store_type, size_sqft FROM stores ORDER BY store_id").fetchall()
    docs = []
    for s in stores:
        rows = conn.execute(
            "SELECT sa.record_date AS date, sa.weekly_sales, sa.is_holiday, "
            "       sf.temperature, sf.fuel_price, sf.cpi, sf.unemployment "
            "FROM sales sa "
            "LEFT JOIN store_features sf "
            "  ON sa.store_id = sf.store_id AND sa.record_date = sf.record_date "
            "WHERE sa.store_id = ? ORDER BY sa.record_date",
            (s["store_id"],),
        ).fetchall()
        readings = [{
            "date": r["date"],
            "weekly_sales": _round(r["weekly_sales"], 2),
            "is_holiday": bool(r["is_holiday"]),
            "temperature": _round(r["temperature"], 2),
            "fuel_price": _round(r["fuel_price"], 3),
            "cpi": _round(r["cpi"], 3),
            "unemployment": _round(r["unemployment"], 2),
        } for r in rows]
        docs.append({"store_id": int(s["store_id"]), "store_type": s["store_type"],
                     "store_size": int(s["size_sqft"]), "readings": readings})
    conn.close()
    return docs


def seed_if_empty():
    if collection.count_documents({}) == 0:
        collection.insert_many(build_documents())
        collection.create_index("store_id")


seed_if_empty()


# ---
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "walmart-mongo-api",
        "database": "MongoDB (mongomock) -- walmart_ts.sales_series",
        "documents": collection.count_documents({}),
        "endpoints": [
            "POST   /mongo/readings",
            "GET    /mongo/readings/<store_id>",
            "PUT    /mongo/readings/<store_id>/<date>",
            "DELETE /mongo/readings/<store_id>/<date>",
            "GET    /mongo/readings/<store_id>/latest",
            "GET    /mongo/readings/<store_id>/range?start=&end=",
        ],
    })


#  CREATE (append a reading) 
@app.route("/mongo/readings", methods=["POST"])
def add_reading():
    data = request.get_json(silent=True) or {}
    required = ["store_id", "date", "weekly_sales"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"missing required fields: {missing}"}), 400
    if not valid_date(data["date"]):
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400

    doc = collection.find_one({"store_id": data["store_id"]})
    if doc is None:
        return jsonify({"error": f"store_id {data['store_id']} does not exist"}), 404
    if any(r["date"] == data["date"] for r in doc["readings"]):
        return jsonify({"error": f"reading for {data['date']} already exists"}), 409

    reading = {
        "date": data["date"],
        "weekly_sales": data["weekly_sales"],
        "is_holiday": data.get("is_holiday", False),
        "temperature": data.get("temperature"),
        "fuel_price": data.get("fuel_price"),
        "cpi": data.get("cpi"),
        "unemployment": data.get("unemployment"),
    }
    collection.update_one({"store_id": data["store_id"]}, {"$push": {"readings": reading}})
    return jsonify({"status": "created", "store_id": data["store_id"], "reading": reading}), 201


# READ (full series) 
@app.route("/mongo/readings/<int:store_id>", methods=["GET"])
def get_series(store_id):
    doc = collection.find_one({"store_id": store_id})
    if doc is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(strip_id(doc))


# UPDATE (one dated reading) 
@app.route("/mongo/readings/<int:store_id>/<date>", methods=["PUT"])
def update_reading(store_id, date):
    data = request.get_json(silent=True) or {}
    set_fields = {}
    if "weekly_sales" in data:
        set_fields["readings.$.weekly_sales"] = data["weekly_sales"]
    if "is_holiday" in data:
        set_fields["readings.$.is_holiday"] = data["is_holiday"]
    if not set_fields:
        return jsonify({"error": "provide weekly_sales and/or is_holiday"}), 400

    result = collection.update_one(
        {"store_id": store_id, "readings.date": date},
        {"$set": set_fields},
    )
    if result.matched_count == 0:
        return jsonify({"error": "store or dated reading not found"}), 404
    return jsonify({"status": "updated", "store_id": store_id, "date": date})


# DELETE (one dated reading) 
@app.route("/mongo/readings/<int:store_id>/<date>", methods=["DELETE"])
def delete_reading(store_id, date):
    doc = collection.find_one({"store_id": store_id})
    if doc is None:
        return jsonify({"error": "store not found"}), 404
    if not any(r["date"] == date for r in doc["readings"]):
        return jsonify({"error": f"no reading dated {date}"}), 404
    collection.update_one({"store_id": store_id}, {"$pull": {"readings": {"date": date}}})
    return jsonify({"status": "deleted", "store_id": store_id, "date": date})


# TIME-SERIES: latest reading 
@app.route("/mongo/readings/<int:store_id>/latest", methods=["GET"])
def latest_reading(store_id):
    doc = collection.find_one({"store_id": store_id})
    if doc is None or not doc["readings"]:
        return jsonify({"error": "not found"}), 404
    return jsonify(max(doc["readings"], key=lambda r: r["date"]))


# TIME-SERIES: readings in a date range 
@app.route("/mongo/readings/<int:store_id>/range", methods=["GET"])
def readings_range(store_id):
    start = request.args.get("start")
    end = request.args.get("end")
    if not start or not end:
        return jsonify({"error": "start and end query params required"}), 400
    if not valid_date(start) or not valid_date(end):
        return jsonify({"error": "start and end must be YYYY-MM-DD"}), 400
    doc = collection.find_one({"store_id": store_id})
    if doc is None:
        return jsonify({"error": "not found"}), 404
    in_range = sorted([r for r in doc["readings"] if start <= r["date"] <= end],
                      key=lambda r: r["date"])
    return jsonify(in_range)


if __name__ == "__main__":
    app.run(port=5002, debug=False)
