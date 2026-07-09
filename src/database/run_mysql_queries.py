"""
Task 2 - Run analytical SQL queries against the SQLite database and save
formatted results to reports/sql_query_results.md.

The queries cover:
  Q1: latest record for a given store
  Q2: records within a date range
  Q3: average weekly sales grouped by store type (cross-table JOIN)
  Q4: total sales vs average temperature per store (cross-table JOIN)
"""
import sqlite3
import pandas as pd
from pathlib import Path

# ── resolve project root (two levels up: src/database/ -> root)
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "walmart_ts.db"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH)

queries = {
    "Q1_latest_record": """
        SELECT store_id, record_date, weekly_sales
        FROM sales WHERE store_id = 1
        ORDER BY record_date DESC LIMIT 1;
    """,
    "Q2_date_range": """
        SELECT store_id, record_date, weekly_sales
        FROM sales WHERE store_id = 1
        AND record_date BETWEEN '2011-01-01' AND '2011-03-31'
        ORDER BY record_date;
    """,
    "Q3_avg_by_store_type": """
        SELECT st.store_type, ROUND(AVG(s.weekly_sales), 2) AS avg_weekly_sales
        FROM sales s JOIN stores st ON s.store_id = st.store_id
        GROUP BY st.store_type ORDER BY avg_weekly_sales DESC;
    """,
    "Q4_sales_vs_temp": """
        SELECT s.store_id, ROUND(SUM(s.weekly_sales), 2) AS total_sales,
               ROUND(AVG(f.temperature), 2) AS avg_temperature
        FROM sales s JOIN store_features f
            ON s.store_id = f.store_id AND s.record_date = f.record_date
        GROUP BY s.store_id ORDER BY total_sales DESC LIMIT 10;
    """
}

with open(REPORTS / "sql_query_results.md", "w") as f:
    for name, q in queries.items():
        result = pd.read_sql_query(q, conn)
        print(f"\n--- {name} ---")
        print(result.to_string(index=False))
        f.write(f"## {name}\n\n```sql\n{q.strip()}\n```\n\n")
        f.write(result.to_markdown(index=False) + "\n\n")

conn.close()
print(f"\nSaved results to {REPORTS / 'sql_query_results.md'}")
