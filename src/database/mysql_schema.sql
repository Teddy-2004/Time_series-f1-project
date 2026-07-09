-- ============================================================
-- Task 2: Relational Database Schema (MySQL)
-- Walmart Store Sales Forecasting dataset
-- ALIGNED WITH TEAMMATE'S APPROACH: sales aggregated at STORE
-- level (summed across departments), not store+dept.
-- 3 tables: stores (dimension), store_features (time-varying
-- external variables), sales (fact table / forecasting target)
-- ============================================================

CREATE DATABASE IF NOT EXISTS walmart_ts;
USE walmart_ts;

DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS store_features;
DROP TABLE IF EXISTS stores;

-- 1) Dimension table: one row per store, attributes that don't change weekly
CREATE TABLE stores (
    store_id     INT PRIMARY KEY,
    store_type   CHAR(1) NOT NULL,           -- 'A', 'B', or 'C'
    size_sqft    INT NOT NULL
);

-- 2) External/context variables, one row per store per week
CREATE TABLE store_features (
    feature_id    INT AUTO_INCREMENT PRIMARY KEY,
    store_id      INT NOT NULL,
    record_date   DATE NOT NULL,
    temperature   DECIMAL(6,2),
    fuel_price    DECIMAL(6,3),
    markdown1     DECIMAL(10,2),
    markdown2     DECIMAL(10,2),
    markdown3     DECIMAL(10,2),
    markdown4     DECIMAL(10,2),
    markdown5     DECIMAL(10,2),
    cpi           DECIMAL(8,3),
    unemployment  DECIMAL(5,2),
    is_holiday    BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (store_id) REFERENCES stores(store_id) ON DELETE CASCADE,
    UNIQUE KEY uq_store_date (store_id, record_date),
    INDEX idx_features_date (record_date)
);

-- 3) Fact table: the forecasting target, one row per store/week
--    (Weekly_Sales summed across all departments for that store)
CREATE TABLE sales (
    sale_id       INT AUTO_INCREMENT PRIMARY KEY,
    store_id      INT NOT NULL,
    record_date   DATE NOT NULL,
    weekly_sales  DECIMAL(14,2) NOT NULL,
    is_holiday    BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (store_id) REFERENCES stores(store_id) ON DELETE CASCADE,
    UNIQUE KEY uq_store_date (store_id, record_date),
    INDEX idx_sales_date (record_date),
    INDEX idx_sales_store_date (store_id, record_date)
);
