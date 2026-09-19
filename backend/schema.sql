-- Schema for Jen & Albert Paminta Management System
-- Compatible with MySQL 8.0+ and TiDB Serverless

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    category_id INT,
    unit VARCHAR(30) DEFAULT 'pack', -- e.g., 'kg', 'pack', 'bottle', 'box'
    unit_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    cost_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    beginning_stock DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    current_stock DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    min_stock_alert DECIMAL(10, 2) NOT NULL DEFAULT 10.00,
    description TEXT,
    image_url VARCHAR(255) DEFAULT '',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sku (sku),
    INDEX idx_category (category_id)
);

-- Inventory Movement Ledger: Tracks all adds, less/deductions, sales, adjustments
CREATE TABLE IF NOT EXISTS inventory_movements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    movement_type VARCHAR(30) NOT NULL, -- 'BEGINNING_BALANCE', 'STOCK_IN', 'SALE_DEDUCTION', 'ADJUSTMENT_LESS', 'ADJUSTMENT_ADD'
    quantity DECIMAL(10, 2) NOT NULL,
    previous_stock DECIMAL(10, 2) NOT NULL,
    new_stock DECIMAL(10, 2) NOT NULL,
    reference_id VARCHAR(100) DEFAULT NULL, -- e.g., Sale Invoice #, PO #, Adjustment ID
    reference_type VARCHAR(50) DEFAULT 'MANUAL', -- 'SALE', 'RESTOCK', 'DAMAGE', 'SPOILAGE', 'AUDIT'
    notes TEXT,
    created_by VARCHAR(50) DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_product_id (product_id),
    INDEX idx_movement_type (movement_type),
    INDEX idx_created_at (created_at)
);

-- Daily/Periodic Inventory Snapshots (for Beginning vs Ending Audits)
CREATE TABLE IF NOT EXISTS inventory_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    product_id INT NOT NULL,
    beginning_stock DECIMAL(10, 2) NOT NULL,
    total_stock_in DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    total_sales_out DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    total_adjustments DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    ending_stock DECIMAL(10, 2) NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_date_product (snapshot_date, product_id)
);

-- Sales Table
CREATE TABLE IF NOT EXISTS sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    customer_name VARCHAR(100) DEFAULT 'Walk-in Customer',
    customer_contact VARCHAR(50) DEFAULT '',
    subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    discount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    tax DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    payment_method VARCHAR(30) NOT NULL DEFAULT 'CASH', -- 'CASH', 'GCASH', 'CARD', 'COD'
    amount_tendered DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    change_due DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(30) NOT NULL DEFAULT 'COMPLETED', -- 'COMPLETED', 'CANCELLED'
    notes TEXT,
    created_by VARCHAR(50) DEFAULT 'staff',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_invoice (invoice_number),
    INDEX idx_created_at (created_at)
);

-- Sale Items Table
CREATE TABLE IF NOT EXISTS sale_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT NOT NULL,
    product_id INT NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    unit VARCHAR(30) DEFAULT 'pack',
    unit_price DECIMAL(10, 2) NOT NULL,
    cost_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    quantity DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sale_id (sale_id),
    INDEX idx_product_id (product_id)
);

-- System & Estate Settings
CREATE TABLE IF NOT EXISTS settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(50) NOT NULL UNIQUE,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

