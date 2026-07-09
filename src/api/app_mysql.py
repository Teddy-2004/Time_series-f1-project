"""
Task 3 - CRUD + time-series API for the relational database.

Aligned with the team's Task 2: reads the same SQLite database
(data/walmart_ts.db) built by src/database/setup_mysql_db.py, with the same
store-level schema (stores, store_features, sales). Weekly_Sales is summed
across departments, so a sales row is keyed by (store_id, record_date) -- no
dept_id.

Endpoints
---------
GET    /                                         health check + endpoint list
POST   /sql/sales                                create a sales record
GET    /sql/sales?store_id=&limit=               list records
GET    /sql/sales/<sale_id>                      read one by primary key
PUT    /sql/sales/<sale_id>                      update a record
DELETE /sql/sales/<sale_id>                      delete a record
GET    /sql/sales/latest?store_id=               latest record for a store   (time-series)
GET    /sql/sales/range?store_id=&start=&end=    records in a date range      (time-series)

Run:
    python3 src/api/app_mysql.py        # serves on http://localhost:5001
"""
from pathlib import Path
from datetime import datetime
import sqlite3
from flask import Flask, request, jsonify

# same project-root resolution as the Task 2 setup scripts
ROOT = Path(__file__).resolve().parents[2]          # src/api/ -> project root
DB_PATH = str(ROOT / "data" / "walmart_ts.db")

app = Flask(__name__)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def valid_date(s):
    try:
        datetime.strptime(str(s), "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def store_exists(conn, store_id):
    return conn.execute("SELECT 1 FROM stores WHERE store_id=?",
                        (store_id,)).fetchone() is not None


# ---
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "walmart-sql-api",
        "database": "relational (SQLite build of the Task 2 MySQL schema)",
        "endpoints": [
            "POST   /sql/sales",
            "GET    /sql/sales?store_id=&limit=",
            "GET    /sql/sales/<sale_id>",
            "PUT    /sql/sales/<sale_id>",
            "DELETE /sql/sales/<sale_id>",
            "GET    /sql/sales/latest?store_id=",
            "GET    /sql/sales/range?store_id=&start=&end=",
        ],
    })


# CREATE 
@app.route("/sql/sales", methods=["POST"])
def create_sale():
    data = request.get_json(silent=True) or {}
    required = ["store_id", "record_date", "weekly_sales"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"missing required fields: {missing}"}), 400
    if not valid_date(data["record_date"]):
        return jsonify({"error": "record_date must be YYYY-MM-DD"}), 400

    conn = get_conn()
    try:
        if not store_exists(conn, data["store_id"]):
            return jsonify({"error": f"store_id {data['store_id']} does not exist"}), 404
        cur = conn.execute(
            "INSERT INTO sales (store_id, record_date, weekly_sales, is_holiday) "
            "VALUES (?, ?, ?, ?)",
            (data["store_id"], data["record_date"], data["weekly_sales"],
             int(data.get("is_holiday", 0))),
        )
        conn.commit()
        return jsonify({"sale_id": cur.lastrowid, **data}), 201
    except sqlite3.IntegrityError as e:
        return jsonify({"error": f"duplicate or constraint violation: {e}"}), 409
    finally:
        conn.close()


# READ (list + by id)
@app.route("/sql/sales", methods=["GET"])
def list_sales():
    store_id = request.args.get("store_id", type=int)
    limit = request.args.get("limit", default=50, type=int)
    conn = get_conn()
    if store_id is not None:
        rows = conn.execute("SELECT * FROM sales WHERE store_id=? "
                            "ORDER BY record_date DESC LIMIT ?", (store_id, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM sales ORDER BY record_date DESC LIMIT ?",
                            (limit,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/sql/sales/<int:sale_id>", methods=["GET"])
def get_sale(sale_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM sales WHERE sale_id=?", (sale_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


# UPDATE 
@app.route("/sql/sales/<int:sale_id>", methods=["PUT"])
def update_sale(sale_id):
    data = request.get_json(silent=True) or {}
    if "record_date" in data and not valid_date(data["record_date"]):
        return jsonify({"error": "record_date must be YYYY-MM-DD"}), 400
    conn = get_conn()
    existing = conn.execute("SELECT * FROM sales WHERE sale_id=?", (sale_id,)).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "not found"}), 404
    fields = {**dict(existing), **data}
    conn.execute(
        "UPDATE sales SET store_id=?, record_date=?, weekly_sales=?, is_holiday=? "
        "WHERE sale_id=?",
        (fields["store_id"], fields["record_date"], fields["weekly_sales"],
         int(fields["is_holiday"]), sale_id),
    )
    conn.commit()
    conn.close()
    return jsonify(fields)


# DELETE 
@app.route("/sql/sales/<int:sale_id>", methods=["DELETE"])
def delete_sale(sale_id):
    conn = get_conn()
    cur = conn.execute("DELETE FROM sales WHERE sale_id=?", (sale_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": sale_id})


# TIME-SERIES: latest record 
@app.route("/sql/sales/latest", methods=["GET"])
def latest_sale():
    store_id = request.args.get("store_id", type=int)
    if store_id is None:
        return jsonify({"error": "store_id query param required"}), 400
    conn = get_conn()
    row = conn.execute("SELECT * FROM sales WHERE store_id=? "
                       "ORDER BY record_date DESC LIMIT 1", (store_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


# TIME-SERIES: records in a date range
@app.route("/sql/sales/range", methods=["GET"])
def sales_in_range():
    store_id = request.args.get("store_id", type=int)
    start = request.args.get("start")
    end = request.args.get("end")
    if store_id is None or not start or not end:
        return jsonify({"error": "store_id, start, end query params required"}), 400
    if not valid_date(start) or not valid_date(end):
        return jsonify({"error": "start and end must be YYYY-MM-DD"}), 400
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM sales WHERE store_id=? AND record_date BETWEEN ? AND ? "
        "ORDER BY record_date", (store_id, start, end)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run(port=5001, debug=False)
