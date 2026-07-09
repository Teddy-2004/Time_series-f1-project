"""
Task 3 - end-to-end test of every API endpoint for BOTH databases, using
Flask's test client. Prints a PASS/FAIL log.

Run:
    python3 src/api/test_endpoints.py

Prerequisite: the SQLite DB exists (run src/database/setup_mysql_db.py first).
The Mongo API seeds its own in-memory collection on import.
"""
import json
import app_mysql
import app_mongo

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, condition, detail=""):
    results.append(PASS if condition else FAIL)
    print(f"[{PASS if condition else FAIL}] {name}" + (f"  -> {detail}" if detail else ""))


def body(resp):
    return json.loads(resp.data)


# SQL API 
print("=" * 70 + "\nSQL API  (relational)\n" + "=" * 70)
sql = app_mysql.app.test_client()

r = sql.get("/sql/sales/latest?store_id=1")
check("SQL GET latest record (store 1)", r.status_code == 200 and "record_date" in body(r),
      f"latest_date={body(r).get('record_date')}")

r = sql.get("/sql/sales/range?store_id=1&start=2011-01-01&end=2011-03-31")
check("SQL GET records by date range", r.status_code == 200 and len(body(r)) > 0,
      f"{len(body(r))} rows")

r = sql.post("/sql/sales", json={"store_id": 1, "record_date": "2099-12-31",
                                 "weekly_sales": 12345.67, "is_holiday": 0})
new_id = body(r).get("sale_id")
check("SQL POST create record", r.status_code == 201 and new_id is not None, f"sale_id={new_id}")

r = sql.get(f"/sql/sales/{new_id}")
check("SQL GET record by id", r.status_code == 200 and body(r)["weekly_sales"] == 12345.67)

r = sql.put(f"/sql/sales/{new_id}", json={"weekly_sales": 99999.99})
check("SQL PUT update record", r.status_code == 200 and body(r)["weekly_sales"] == 99999.99)

r = sql.delete(f"/sql/sales/{new_id}")
check("SQL DELETE record", r.status_code == 200 and body(r).get("deleted") == new_id)

check("SQL GET deleted record -> 404", sql.get(f"/sql/sales/{new_id}").status_code == 404)
check("SQL POST unknown store -> 404",
      sql.post("/sql/sales", json={"store_id": 999999, "record_date": "2099-01-01",
                                   "weekly_sales": 1}).status_code == 404)
check("SQL POST missing fields -> 400",
      sql.post("/sql/sales", json={"store_id": 1}).status_code == 400)


# Mongo API
print("\n" + "=" * 70 + "\nMongoDB API\n" + "=" * 70)
mon = app_mongo.app.test_client()

r = mon.get("/mongo/readings/1/latest")
check("Mongo GET latest reading (store 1)", r.status_code == 200 and "date" in body(r),
      f"latest_date={body(r).get('date')}")

r = mon.get("/mongo/readings/1/range?start=2011-01-01&end=2011-03-31")
check("Mongo GET readings by date range", r.status_code == 200 and len(body(r)) > 0,
      f"{len(body(r))} readings")

r = mon.post("/mongo/readings", json={"store_id": 1, "date": "2099-12-31",
                                      "weekly_sales": 55555.55})
check("Mongo POST append reading", r.status_code == 201, body(r).get("status"))

r = mon.get("/mongo/readings/1")
check("Mongo GET full series (new reading present)",
      r.status_code == 200 and any(rd["date"] == "2099-12-31" for rd in body(r)["readings"]))

check("Mongo PUT update reading",
      mon.put("/mongo/readings/1/2099-12-31", json={"weekly_sales": 77777.77}).status_code == 200)
r = mon.get("/mongo/readings/1/range?start=2099-12-31&end=2099-12-31")
check("Mongo update reflected", body(r)[0]["weekly_sales"] == 77777.77,
      f"weekly_sales={body(r)[0]['weekly_sales']}")

check("Mongo DELETE reading", mon.delete("/mongo/readings/1/2099-12-31").status_code == 200)
check("Mongo DELETE same reading again -> 404",
      mon.delete("/mongo/readings/1/2099-12-31").status_code == 404)
check("Mongo POST unknown store -> 404",
      mon.post("/mongo/readings", json={"store_id": 999999, "date": "2099-01-01",
                                        "weekly_sales": 1}).status_code == 404)
check("Mongo GET unknown store latest -> 404",
      mon.get("/mongo/readings/999999/latest").status_code == 404)


#  Summary 
passed, total = results.count(PASS), len(results)
print("\n" + "=" * 70 + f"\nSUMMARY: {passed}/{total} checks passed\n" + "=" * 70)
if passed != total:
    raise SystemExit(1)
