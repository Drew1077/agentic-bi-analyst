-- ============================================================
-- Agentic BI Analyst
-- MySQL Database Schema
-- Dataset Version: v1.0
-- ============================================================

CREATE DATABASE IF NOT EXISTS agentic_bi
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE agentic_bi;

-- ============================================================
-- 1. CALENDAR
-- ============================================================

CREATE TABLE IF NOT EXISTS calendar (
    date DATE PRIMARY KEY,
    day TINYINT UNSIGNED NOT NULL,
    month TINYINT UNSIGNED NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter TINYINT UNSIGNED NOT NULL,
    year SMALLINT UNSIGNED NOT NULL,
    week TINYINT UNSIGNED NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    holiday_name VARCHAR(100) NULL,
    is_holiday BOOLEAN NOT NULL,
    fiscal_year VARCHAR(9) NOT NULL,
    fiscal_quarter TINYINT UNSIGNED NOT NULL,
    season VARCHAR(20) NOT NULL,

    CONSTRAINT chk_calendar_day
        CHECK (day BETWEEN 1 AND 31),

    CONSTRAINT chk_calendar_month
        CHECK (month BETWEEN 1 AND 12),

    CONSTRAINT chk_calendar_quarter
        CHECK (quarter BETWEEN 1 AND 4),

    CONSTRAINT chk_calendar_week
        CHECK (week BETWEEN 1 AND 53),

    CONSTRAINT chk_calendar_fiscal_quarter
        CHECK (fiscal_quarter BETWEEN 1 AND 4)
) ENGINE=InnoDB;


-- ============================================================
-- 2. STORES
-- ============================================================

CREATE TABLE IF NOT EXISTS stores (
    store_id VARCHAR(10) PRIMARY KEY,
    store_name VARCHAR(100) NOT NULL,
    store_type VARCHAR(30) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    region VARCHAR(30) NOT NULL,
    opening_date DATE NOT NULL,
    store_size_sqft INT UNSIGNED NOT NULL,
    status VARCHAR(30) NOT NULL,

    CONSTRAINT chk_store_size
        CHECK (store_size_sqft >= 0),

    INDEX idx_stores_region (region),
    INDEX idx_stores_city (city),
    INDEX idx_stores_status (status)
) ENGINE=InnoDB;


-- ============================================================
-- 3. PRODUCTS
-- ============================================================

CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(12) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100) NOT NULL,
    brand VARCHAR(100) NOT NULL,
    unit_cost DECIMAL(12,2) NOT NULL,
    base_price DECIMAL(12,2) NOT NULL,
    launch_date DATE NOT NULL,
    product_status VARCHAR(30) NOT NULL,
    supplier_region VARCHAR(30) NOT NULL,
    weight_kg DECIMAL(8,2) NOT NULL,
    rating DECIMAL(3,2) NULL,
    rating_count INT UNSIGNED NOT NULL,

    CONSTRAINT chk_product_unit_cost
        CHECK (unit_cost >= 0),

    CONSTRAINT chk_product_base_price
        CHECK (base_price >= 0),

    CONSTRAINT chk_product_weight
        CHECK (weight_kg >= 0),

    CONSTRAINT chk_product_rating
        CHECK (rating IS NULL OR rating BETWEEN 0 AND 5),

    INDEX idx_products_category (category),
    INDEX idx_products_subcategory (subcategory),
    INDEX idx_products_brand (brand),
    INDEX idx_products_status (product_status),
    INDEX idx_products_supplier_region (supplier_region)
) ENGINE=InnoDB;


-- ============================================================
-- 4. CUSTOMERS
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(12) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    gender VARCHAR(30) NOT NULL,
    birth_year SMALLINT UNSIGNED NOT NULL,
    signup_date DATE NOT NULL,
    customer_segment VARCHAR(50) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    region VARCHAR(30) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    acquisition_channel VARCHAR(50) NOT NULL,
    preferred_device VARCHAR(30) NOT NULL,
    customer_status VARCHAR(30) NOT NULL,

    CONSTRAINT uq_customers_email
        UNIQUE (email),

    INDEX idx_customers_signup_date (signup_date),
    INDEX idx_customers_segment (customer_segment),
    INDEX idx_customers_region (region),
    INDEX idx_customers_acquisition (acquisition_channel),
    INDEX idx_customers_status (customer_status)
) ENGINE=InnoDB;


-- ============================================================
-- 5. ORDERS
-- ============================================================

CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(12) PRIMARY KEY,
    customer_id VARCHAR(12) NOT NULL,
    store_id VARCHAR(10) NOT NULL,
    order_date DATE NOT NULL,
    order_timestamp DATETIME NOT NULL,
    order_status VARCHAR(30) NOT NULL,
    payment_status VARCHAR(30) NOT NULL,
    shipping_method VARCHAR(50) NOT NULL,
    delivery_date DATE NULL,
    shipping_fee DECIMAL(12,2) NOT NULL,
    discount_amount DECIMAL(12,2) NOT NULL,
    tax_amount DECIMAL(12,2) NOT NULL,
    order_total DECIMAL(14,2) NOT NULL,

    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id),

    CONSTRAINT fk_orders_store
        FOREIGN KEY (store_id)
        REFERENCES stores(store_id),

    CONSTRAINT chk_orders_shipping_fee
        CHECK (shipping_fee >= 0),

    CONSTRAINT chk_orders_discount
        CHECK (discount_amount >= 0),

    CONSTRAINT chk_orders_tax
        CHECK (tax_amount >= 0),

    CONSTRAINT chk_orders_total
        CHECK (order_total >= 0),

    INDEX idx_orders_customer (customer_id),
    INDEX idx_orders_store (store_id),
    INDEX idx_orders_date (order_date),
    INDEX idx_orders_timestamp (order_timestamp),
    INDEX idx_orders_status (order_status),
    INDEX idx_orders_payment_status (payment_status)
) ENGINE=InnoDB;


-- ============================================================
-- 6. ORDER ITEMS
-- ============================================================

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id VARCHAR(12) PRIMARY KEY,
    order_id VARCHAR(12) NOT NULL,
    product_id VARCHAR(12) NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    unit_cost DECIMAL(12,2) NOT NULL,
    discount_percent DECIMAL(7,4) NOT NULL,
    discount_amount DECIMAL(14,2) NOT NULL,
    gross_revenue DECIMAL(14,2) NOT NULL,
    net_revenue DECIMAL(14,2) NOT NULL,
    total_cost DECIMAL(14,2) NOT NULL,
    gross_profit DECIMAL(14,2) NOT NULL,

    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id),

    CONSTRAINT chk_order_items_quantity
        CHECK (quantity > 0),

    CONSTRAINT chk_order_items_unit_price
        CHECK (unit_price >= 0),

    CONSTRAINT chk_order_items_unit_cost
        CHECK (unit_cost >= 0),

    CONSTRAINT chk_order_items_discount_percent
        CHECK (discount_percent BETWEEN 0 AND 1),

    CONSTRAINT chk_order_items_discount_amount
        CHECK (discount_amount >= 0),

    INDEX idx_order_items_order (order_id),
    INDEX idx_order_items_product (product_id)
) ENGINE=InnoDB;


-- ============================================================
-- 7. PAYMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR(15) PRIMARY KEY,
    order_id VARCHAR(12) NOT NULL,
    payment_date DATE NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    payment_status VARCHAR(30) NOT NULL,
    amount DECIMAL(14,2) NOT NULL,
    transaction_reference VARCHAR(50) NOT NULL,
    refund_amount DECIMAL(14,2) NOT NULL,

    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    CONSTRAINT uq_payments_transaction_reference
        UNIQUE (transaction_reference),

    CONSTRAINT chk_payments_amount
        CHECK (amount >= 0),

    CONSTRAINT chk_payments_refund
        CHECK (refund_amount >= 0),

    INDEX idx_payments_order (order_id),
    INDEX idx_payments_date (payment_date),
    INDEX idx_payments_status (payment_status)
) ENGINE=InnoDB;


-- ============================================================
-- 8. RETURNS
-- ============================================================

CREATE TABLE IF NOT EXISTS returns (
    return_id VARCHAR(15) PRIMARY KEY,
    order_id VARCHAR(12) NOT NULL,
    order_item_id VARCHAR(15) NOT NULL,
    return_date DATE NOT NULL,
    return_quantity INT UNSIGNED NOT NULL,
    return_reason VARCHAR(100) NOT NULL,
    refund_amount DECIMAL(14,2) NOT NULL,
    return_status VARCHAR(30) NOT NULL,
    `condition` VARCHAR(50) NOT NULL,

    CONSTRAINT fk_returns_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    CONSTRAINT fk_returns_order_item
        FOREIGN KEY (order_item_id)
        REFERENCES order_items(order_item_id),

    CONSTRAINT chk_returns_quantity
        CHECK (return_quantity > 0),

    CONSTRAINT chk_returns_refund
        CHECK (refund_amount >= 0),

    INDEX idx_returns_order (order_id),
    INDEX idx_returns_order_item (order_item_id),
    INDEX idx_returns_date (return_date),
    INDEX idx_returns_reason (return_reason),
    INDEX idx_returns_status (return_status)
) ENGINE=InnoDB;


-- ============================================================
-- 9. MARKETING SPEND
-- ============================================================

CREATE TABLE IF NOT EXISTS marketing_spend (
    marketing_id VARCHAR(15) PRIMARY KEY,
    date DATE NOT NULL,
    channel VARCHAR(50) NOT NULL,
    campaign_name VARCHAR(150) NOT NULL,
    region VARCHAR(30) NOT NULL,
    spend DECIMAL(14,2) NOT NULL,
    impressions BIGINT UNSIGNED NOT NULL,
    clicks BIGINT UNSIGNED NOT NULL,
    conversions BIGINT UNSIGNED NOT NULL,

    CONSTRAINT fk_marketing_date
        FOREIGN KEY (date)
        REFERENCES calendar(date),

    CONSTRAINT chk_marketing_spend
        CHECK (spend >= 0),

    INDEX idx_marketing_date (date),
    INDEX idx_marketing_channel (channel),
    INDEX idx_marketing_region (region),
    INDEX idx_marketing_date_channel (date, channel)
) ENGINE=InnoDB;


-- ============================================================
-- 10. INVENTORY SNAPSHOTS
-- ============================================================

CREATE TABLE IF NOT EXISTS inventory_snapshots (
    snapshot_id VARCHAR(15) PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    store_id VARCHAR(10) NOT NULL,
    product_id VARCHAR(12) NOT NULL,
    opening_stock INT UNSIGNED NOT NULL,
    units_received INT UNSIGNED NOT NULL,
    units_sold INT UNSIGNED NOT NULL,
    units_returned INT UNSIGNED NOT NULL,
    closing_stock INT UNSIGNED NOT NULL,
    reorder_level INT UNSIGNED NOT NULL,
    stockout_flag BOOLEAN NOT NULL,

    CONSTRAINT fk_inventory_date
        FOREIGN KEY (snapshot_date)
        REFERENCES calendar(date),

    CONSTRAINT fk_inventory_store
        FOREIGN KEY (store_id)
        REFERENCES stores(store_id),

    CONSTRAINT fk_inventory_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id),

    CONSTRAINT chk_inventory_stockout
        CHECK (stockout_flag IN (0, 1)),

    INDEX idx_inventory_date (snapshot_date),
    INDEX idx_inventory_store (store_id),
    INDEX idx_inventory_product (product_id),
    INDEX idx_inventory_date_store_product
        (snapshot_date, store_id, product_id),
    INDEX idx_inventory_product_date
        (product_id, snapshot_date)
) ENGINE=InnoDB;