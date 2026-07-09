-- ============================================================
-- Task 2: Example queries against the relational schema
-- (store-level granularity, aligned with teammate's approach)
-- ============================================================

-- Query 1: Latest record for a given store ("latest record" requirement)
SELECT store_id, record_date, weekly_sales
FROM sales
WHERE store_id = 1
ORDER BY record_date DESC
LIMIT 1;

-- Query 2: Records for a store within a date range ("date range" requirement)
SELECT store_id, record_date, weekly_sales
FROM sales
WHERE store_id = 1
  AND record_date BETWEEN '2011-01-01' AND '2011-03-31'
ORDER BY record_date;

-- Query 3: Average weekly sales by store type, joining sales -> stores
SELECT st.store_type, ROUND(AVG(s.weekly_sales), 2) AS avg_weekly_sales
FROM sales s
JOIN stores st ON s.store_id = st.store_id
GROUP BY st.store_type
ORDER BY avg_weekly_sales DESC;

-- Query 4: Total sales vs average temperature per store, joining sales -> store_features
SELECT s.store_id,
       ROUND(SUM(s.weekly_sales), 2) AS total_sales,
       ROUND(AVG(f.temperature), 2) AS avg_temperature
FROM sales s
JOIN store_features f ON s.store_id = f.store_id AND s.record_date = f.record_date
GROUP BY s.store_id
ORDER BY total_sales DESC
LIMIT 10;
