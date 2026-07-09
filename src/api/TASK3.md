# Task 3 — CRUD & Time-Series API Endpoints

Two Flask services provide full CRUD plus the two required time-series query
endpoints (**latest record**, **records by date range**) for **both** Task 2
databases. Built to match the team's Task 2 exactly — same schema, same paths,
same SQLite build and same `sales_series` MongoDB collection.

|                 | SQL service (`app_mysql.py`)                                   | Mongo service (`app_mongo.py`)                 |
| --------------- | -------------------------------------------------------------- | ---------------------------------------------- |
| Backend         | SQLite build of the Task 2 MySQL schema (`data/walmart_ts.db`) | `mongomock` — `walmart_ts.sales_series`        |
| Port            | `5001`                                                         | `5002`                                         |
| Record identity | `sale_id` PK, unique on `(store_id, record_date)`              | `(store_id, date)` inside the `readings` array |

Both use the team's store-level model: `Weekly_Sales` summed across departments,
so a record is one store for one week (no `dept_id`). As in the Task 2 scripts,
SQLite/`mongomock` are drop-in stand-ins for MySQL/MongoDB — swap `get_conn()`
for `mysql.connector` and `mongomock.MongoClient()` for `pymongo.MongoClient(...)`
to point at real servers, with no other changes.

## Run

```bash
pip install -r requirements.txt          # flask, pymongo, mongomock (already in Task 2)

# Task 3 needs only data/walmart_ts.db. If it isn't present, build it with the
# Task 2 script (that step needs preprocessing.py + the Kaggle CSVs):
python3 src/database/setup_mysql_db.py

# verify every endpoint at once (no web server needed)
python3 src/api/test_endpoints.py        # expect: 19/19 checks passed

# OR run the live services (separate terminals)
python3 src/api/app_mysql.py             # http://localhost:5001
python3 src/api/app_mongo.py             # http://localhost:5002
```

## SQL endpoints (`:5001`)

| Method | Path                                     | Purpose                   |
| ------ | ---------------------------------------- | ------------------------- |
| POST   | `/sql/sales`                             | create a record           |
| GET    | `/sql/sales?store_id=&limit=`            | list records              |
| GET    | `/sql/sales/<sale_id>`                   | read one by id            |
| PUT    | `/sql/sales/<sale_id>`                   | update                    |
| DELETE | `/sql/sales/<sale_id>`                   | delete                    |
| GET    | `/sql/sales/latest?store_id=`            | **latest record**         |
| GET    | `/sql/sales/range?store_id=&start=&end=` | **records by date range** |

```bash
curl "http://localhost:5001/sql/sales/latest?store_id=1"
curl "http://localhost:5001/sql/sales/range?store_id=1&start=2011-01-01&end=2011-03-31"
curl -X POST http://localhost:5001/sql/sales \
     -H "Content-Type: application/json" \
     -d '{"store_id":1,"record_date":"2099-12-31","weekly_sales":12345.67}'
curl -X PUT  http://localhost:5001/sql/sales/6436 \
     -H "Content-Type: application/json" -d '{"weekly_sales":99999.99}'
curl -X DELETE http://localhost:5001/sql/sales/6436
```

## MongoDB endpoints (`:5002`)

| Method | Path                                           | Purpose                              |
| ------ | ---------------------------------------------- | ------------------------------------ |
| POST   | `/mongo/readings`                              | append a reading to a store's series |
| GET    | `/mongo/readings/<store_id>`                   | read the full series                 |
| PUT    | `/mongo/readings/<store_id>/<date>`            | update one dated reading             |
| DELETE | `/mongo/readings/<store_id>/<date>`            | delete one dated reading             |
| GET    | `/mongo/readings/<store_id>/latest`            | **latest reading**                   |
| GET    | `/mongo/readings/<store_id>/range?start=&end=` | **readings by date range**           |

```bash
curl "http://localhost:5002/mongo/readings/1/latest"
curl "http://localhost:5002/mongo/readings/1/range?start=2011-01-01&end=2011-03-31"
curl -X POST http://localhost:5002/mongo/readings \
     -H "Content-Type: application/json" \
     -d '{"store_id":1,"date":"2099-12-31","weekly_sales":55555.55}'
curl -X PUT  http://localhost:5002/mongo/readings/1/2099-12-31 \
     -H "Content-Type: application/json" -d '{"weekly_sales":77777.77}'
curl -X DELETE http://localhost:5002/mongo/readings/1/2099-12-31
```

## Status codes

`200` ok · `201` created · `400` bad/missing input · `404` not found (unknown
store, id, or dated reading) · `409` duplicate `(store_id, date)`.

## Notes

- Both services depend only on the Task 2 database file `data/walmart_ts.db`.
  `app_mysql.py` reads it directly; `app_mongo.py` seeds its `sales_series`
  collection from it (joining `sales` + `store_features` + `stores`), producing
  the same documents as `setup_mongodb.py`. No raw CSVs or preprocessing module
  are needed to run Task 3.
- Validation: required-field + `YYYY-MM-DD` checks, store-existence checks
  (404), duplicate `(store_id, date)` (409). Mongo `PUT`/`DELETE` return 404
  when the specific dated reading is absent, not just when the store is missing.
- `test_endpoints.py` covers all of this — 19 checks, all passing.
