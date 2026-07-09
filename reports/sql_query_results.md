## Q1_latest_record

```sql
SELECT store_id, record_date, weekly_sales
        FROM sales WHERE store_id = 1
        ORDER BY record_date DESC LIMIT 1;
```

|   store_id | record_date   |   weekly_sales |
|-----------:|:--------------|---------------:|
|          1 | 2012-10-26    |         376005 |

## Q2_date_range

```sql
SELECT store_id, record_date, weekly_sales
        FROM sales WHERE store_id = 1
        AND record_date BETWEEN '2011-01-01' AND '2011-03-31'
        ORDER BY record_date;
```

|   store_id | record_date   |   weekly_sales |
|-----------:|:--------------|---------------:|
|          1 | 2011-01-07    |         473793 |
|          1 | 2011-01-14    |         486899 |
|          1 | 2011-01-21    |         471907 |
|          1 | 2011-01-28    |         485433 |
|          1 | 2011-02-04    |         486164 |
|          1 | 2011-02-11    |         675119 |
|          1 | 2011-02-18    |         478830 |
|          1 | 2011-02-25    |         481832 |
|          1 | 2011-03-04    |         468343 |
|          1 | 2011-03-11    |         462982 |
|          1 | 2011-03-18    |         463777 |
|          1 | 2011-03-25    |         438805 |

## Q3_avg_by_store_type

```sql
SELECT st.store_type, ROUND(AVG(s.weekly_sales), 2) AS avg_weekly_sales
        FROM sales s JOIN stores st ON s.store_id = st.store_id
        GROUP BY st.store_type ORDER BY avg_weekly_sales DESC;
```

| store_type   |   avg_weekly_sales |
|:-------------|-------------------:|
| A            |             303984 |
| B            |             221018 |
| C            |             123823 |

## Q4_sales_vs_temp

```sql
SELECT s.store_id, ROUND(SUM(s.weekly_sales), 2) AS total_sales,
               ROUND(AVG(f.temperature), 2) AS avg_temperature
        FROM sales s JOIN store_features f
            ON s.store_id = f.store_id AND s.record_date = f.record_date
        GROUP BY s.store_id ORDER BY total_sales DESC LIMIT 10;
```

|   store_id |   total_sales |   avg_temperature |
|-----------:|--------------:|------------------:|
|          1 |   5.67644e+07 |             59.37 |
|         24 |   5.46457e+07 |             47.79 |
|         41 |   5.38307e+07 |             66.75 |
|         22 |   5.22549e+07 |             72.03 |
|         23 |   4.905e+07   |             68.36 |
|         20 |   4.84603e+07 |             63.83 |
|         14 |   4.83511e+07 |             75.81 |
|         40 |   4.81378e+07 |             57.85 |
|         19 |   4.75453e+07 |             62.7  |
|          7 |   4.59979e+07 |             53.76 |

