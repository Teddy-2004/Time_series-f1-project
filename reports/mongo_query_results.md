## Q1: latest record for store 1

```javascript
db.sales_series.find({store_id: 1})  // then take last element of "readings"
```

**Result (sample):**
```json
{
  "date": "2012-10-26",
  "weekly_sales": 376004.77,
  "is_holiday": false,
  "temperature": 52.51,
  "fuel_price": 3.769,
  "cpi": 229.326,
  "unemployment": 7.57
}
```

## Q2: readings in date range for store 1

```javascript
db.sales_series.aggregate([
  { $match: { store_id: 1 } },
  { $project: { readings: { $filter: {
        input: "$readings", as: "r",
        cond: { $and: [
          { $gte: ["$$r.date", "2011-01-01"] },
          { $lte: ["$$r.date", "2011-03-31"] }
        ]}
  }}}}
])
```

**Result (sample):**
```json
[
  {
    "date": "2011-01-07",
    "weekly_sales": 473792.54,
    "is_holiday": false,
    "temperature": 37.84,
    "fuel_price": 2.965,
    "cpi": 215.787,
    "unemployment": 8.06
  },
  {
    "date": "2011-01-14",
    "weekly_sales": 486899.06,
    "is_holiday": false,
    "temperature": 38.34,
    "fuel_price": 3.125,
    "cpi": 217.403,
    "unemployment": 8.33
  },
  {
    "date": "2011-01-21",
    "weekly_sales": 471906.55,
    "is_holiday": false,
    "temperature": 29.3,
    "fuel_price": 3.085,
    "cpi": 217.828,
    "unemployment": 7.94
  }
]
```

## Q3: average weekly sales by store type

```javascript
[
  {
    "$unwind": "$readings"
  },
  {
    "$group": {
      "_id": "$store_type",
      "avg_weekly_sales": {
        "$avg": "$readings.weekly_sales"
      }
    }
  },
  {
    "$sort": {
      "avg_weekly_sales": -1
    }
  }
]
```

**Result (sample):**
```json
[
  {
    "avg_weekly_sales": 303984.3395804196,
    "_id": "A"
  },
  {
    "avg_weekly_sales": 221017.83195304696,
    "_id": "B"
  },
  {
    "avg_weekly_sales": 123823.25655011655,
    "_id": "C"
  }
]
```

## Q4: large stores (size > 150,000 sqft)

```javascript
db.sales_series.find({ store_size: { $gt: 150000 } }, { store_id: 1, store_size: 1 })
```

**Result (sample):**
```json
[
  {
    "store_id": 1,
    "store_size": 219479
  },
  {
    "store_id": 5,
    "store_size": 190757
  },
  {
    "store_id": 6,
    "store_size": 159692
  }
]
```

