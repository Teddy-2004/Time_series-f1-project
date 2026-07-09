# Task 2 - MongoDB Collection Design

ALIGNED WITH TEAMMATE'S APPROACH: sales are aggregated at STORE level
(summed across departments), so each document represents one store's full
weekly time series rather than one store/department pair.

## Collection: sales_series

One document per store. Each document embeds:
- store-level metadata (denormalized from stores.csv: store_type, store_size)
- a "readings" array holding the full weekly time series for that store,
  each entry combining the store-aggregated sales target with that week's
  external features (denormalized from features.csv)

Example (readings array trimmed to 2 entries for readability):

    {
      "store_id": 1,
      "store_type": "A",
      "store_size": 219479,
      "readings": [
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
        }
      ]
    }

Design rationale:
- This is the classic time-series "bucket per entity" pattern: a store's
  entire sales history is almost always queried as a unit (for charting,
  forecasting, lag features), so embedding it avoids the join/lookup
  overhead relational databases require for the equivalent query.
- One document per store (45 total) is a natural, bounded collection size --
  simpler and more predictable than the earlier per-(store,dept) design,
  since department-level detail is no longer tracked separately.
- A single-field index on store_id supports fast lookup of a series;
  "latest record" and "date range" queries (Task 3) then operate on the
  readings array within that one document.
