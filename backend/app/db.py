import os
import sqlite3
import pymysql
import pymysql.cursors
from app.config import Config

_is_mysql = False

def is_mysql_configured():
    return bool(Config.DB_HOST and Config.DB_USER)

def get_raw_connection():
    global _is_mysql
    if is_mysql_configured():
        try:
            connect_kwargs = {
                "host": Config.DB_HOST,
                "port": Config.DB_PORT,
                "user": Config.DB_USER,
                "password": Config.DB_PASSWORD,
                "database": Config.DB_NAME,
                "cursorclass": pymysql.cursors.DictCursor,
                "autocommit": True,
                "charset": "utf8mb4"
            }
            if Config.DB_USE_SSL:
                connect_kwargs["ssl"] = {"ssl": {}}
            conn = pymysql.connect(**connect_kwargs)
            _is_mysql = True
            return conn, True
        except Exception as e:
            print(f"[DB WARN] Failed connecting to TiDB/MySQL at {Config.DB_HOST}:{Config.DB_PORT}. Error: {e}")
            print("[DB INFO] Falling back to local SQLite database (backend/data.db)...")
    
    # SQLite fallback
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data.db"))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _is_mysql = False
    return conn, False

class DB:
    @staticmethod
    def execute_query(sql, params=None, commit=False):
        conn, is_mysql = get_raw_connection()
        cursor = None
        try:
            if not is_mysql:
                # Convert %s placeholders to ? for sqlite
                sqlite_sql = sql.replace("%s", "?")
                cursor = conn.cursor()
                cursor.execute(sqlite_sql, params or ())
                if commit:
                    conn.commit()
                last_id = cursor.lastrowid
                row_count = cursor.rowcount
                return {"last_id": last_id, "row_count": row_count}
            else:
                cursor = conn.cursor()
                cursor.execute(sql, params or ())
                if commit:
                    conn.commit()
                last_id = cursor.lastrowid
                row_count = cursor.rowcount
                return {"last_id": last_id, "row_count": row_count}
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def fetch_all(sql, params=None):
        conn, is_mysql = get_raw_connection()
        cursor = None
        try:
            if not is_mysql:
                sqlite_sql = sql.replace("%s", "?")
                cursor = conn.cursor()
                cursor.execute(sqlite_sql, params or ())
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            else:
                cursor = conn.cursor()
                cursor.execute(sql, params or ())
                rows = cursor.fetchall()
                return list(rows)
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def fetch_one(sql, params=None):
        conn, is_mysql = get_raw_connection()
        cursor = None
        try:
            if not is_mysql:
                sqlite_sql = sql.replace("%s", "?")
                cursor = conn.cursor()
                cursor.execute(sqlite_sql, params or ())
                row = cursor.fetchone()
                return dict(row) if row else None
            else:
                cursor = conn.cursor()
                cursor.execute(sql, params or ())
                row = cursor.fetchone()
                return row
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def get_status():
        conn, is_mysql = get_raw_connection()
        try:
            if is_mysql:
                cursor = conn.cursor()
                cursor.execute("SELECT VERSION() as version, DATABASE() as db_name")
                res = cursor.fetchone()
                cursor.close()
                return {
                    "connected": True,
                    "engine": "TiDB / MySQL",
                    "host": Config.DB_HOST,
                    "port": Config.DB_PORT,
                    "database": res.get("db_name") if res else Config.DB_NAME,
                    "version": res.get("version") if res else "Unknown"
                }
            else:
                return {
                    "connected": True,
                    "engine": "SQLite (Local Fallback)",
                    "host": "localhost",
                    "port": "N/A",
                    "database": "data.db",
                    "version": sqlite3.sqlite_version,
                    "notice": "To connect live to TiDB Cloud or MySQL, configure DB_HOST, DB_USER, DB_PASSWORD in .env or Render environment variables."
                }
        finally:
            conn.close()


def init_db():
    conn, is_mysql = get_raw_connection()
    cursor = conn.cursor()
    try:
        if is_mysql:
            # MySQL / TiDB Table definitions
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                role VARCHAR(20) DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sku VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(150) NOT NULL,
                category_id INT,
                unit VARCHAR(30) DEFAULT 'pack',
                unit_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                cost_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                beginning_stock DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                current_stock DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                min_stock_alert DECIMAL(10, 2) NOT NULL DEFAULT 10.00,
                description TEXT,
                image_url MEDIUMTEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            """)
            try:
                cursor.execute("ALTER TABLE products MODIFY COLUMN image_url MEDIUMTEXT;")
            except Exception:
                pass
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_movements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT NOT NULL,
                movement_type VARCHAR(30) NOT NULL,
                quantity DECIMAL(10, 2) NOT NULL,
                previous_stock DECIMAL(10, 2) NOT NULL,
                new_stock DECIMAL(10, 2) NOT NULL,
                reference_id VARCHAR(100) DEFAULT NULL,
                reference_type VARCHAR(50) DEFAULT 'MANUAL',
                notes TEXT,
                created_by VARCHAR(50) DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
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
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                invoice_number VARCHAR(50) NOT NULL UNIQUE,
                customer_name VARCHAR(100) DEFAULT 'Walk-in Customer',
                customer_contact VARCHAR(50) DEFAULT '',
                subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                discount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                tax DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                payment_method VARCHAR(30) NOT NULL DEFAULT 'CASH',
                amount_tendered DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                change_due DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                status VARCHAR(30) NOT NULL DEFAULT 'COMPLETED',
                notes TEXT,
                created_by VARCHAR(50) DEFAULT 'staff',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                setting_key VARCHAR(50) NOT NULL UNIQUE,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            """)
        else:
            # SQLite Table definitions
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                category_id INTEGER,
                unit TEXT DEFAULT 'pack',
                unit_price REAL NOT NULL DEFAULT 0.00,
                cost_price REAL NOT NULL DEFAULT 0.00,
                beginning_stock REAL NOT NULL DEFAULT 0.00,
                current_stock REAL NOT NULL DEFAULT 0.00,
                min_stock_alert REAL NOT NULL DEFAULT 10.00,
                description TEXT,
                image_url TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                previous_stock REAL NOT NULL,
                new_stock REAL NOT NULL,
                reference_id TEXT DEFAULT NULL,
                reference_type TEXT DEFAULT 'MANUAL',
                notes TEXT,
                created_by TEXT DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                beginning_stock REAL NOT NULL,
                total_stock_in REAL NOT NULL DEFAULT 0.00,
                total_sales_out REAL NOT NULL DEFAULT 0.00,
                total_adjustments REAL NOT NULL DEFAULT 0.00,
                ending_stock REAL NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(snapshot_date, product_id)
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL UNIQUE,
                customer_name TEXT DEFAULT 'Walk-in Customer',
                customer_contact TEXT DEFAULT '',
                subtotal REAL NOT NULL DEFAULT 0.00,
                discount REAL NOT NULL DEFAULT 0.00,
                tax REAL NOT NULL DEFAULT 0.00,
                total_amount REAL NOT NULL DEFAULT 0.00,
                payment_method TEXT NOT NULL DEFAULT 'CASH',
                amount_tendered REAL NOT NULL DEFAULT 0.00,
                change_due REAL NOT NULL DEFAULT 0.00,
                status TEXT NOT NULL DEFAULT 'COMPLETED',
                notes TEXT,
                created_by TEXT DEFAULT 'staff',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                unit TEXT DEFAULT 'pack',
                unit_price REAL NOT NULL,
                cost_price REAL NOT NULL DEFAULT 0.00,
                quantity REAL NOT NULL,
                subtotal REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT NOT NULL UNIQUE,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.commit()

        seed_initial_data(conn, is_mysql)
        print("[DB SUCCESS] Database schema and seed data initialized successfully.")
    finally:
        cursor.close()
        conn.close()


def seed_initial_data(conn, is_mysql):
    cursor = conn.cursor()
    # 1. Admin User
    placeholder = "%s" if is_mysql else "?"
    
    # Check if admin exists
    cursor.execute(f"SELECT id FROM users WHERE username = {placeholder}", ("admin",))
    if not cursor.fetchone():
        # Using sha256 or simple hash for admin
        import hashlib
        pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute(
            f"INSERT INTO users (username, password_hash, full_name, role) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})",
            ("admin", pwd_hash, "Jen & Albert Paminta Estate Admin", "admin")
        )

    # 2. Categories
    categories = [
        ("Paminta & Whole Spices", "Authentic premium whole black and white peppercorn varieties from Paminta harvest"),
        ("Ground & Blended Spices", "Pure freshly milled black pepper and proprietary spice blends"),
        ("Estate Wines & Cellar Reserve", "Handcrafted vineyard wines and exclusive reserve blends"),
        ("Fresh Harvest & Table Grapes", "Handpicked fresh vineyard grape clusters and farm produce"),
        ("Heritage Gift Packs", "Curated luxury gift boxes pairing Paminta spices and estate wines")
    ]
    for cat_name, cat_desc in categories:
        cursor.execute(f"SELECT id FROM categories WHERE name = {placeholder}", (cat_name,))
        if not cursor.fetchone():
            cursor.execute(
                f"INSERT INTO categories (name, description) VALUES ({placeholder}, {placeholder})",
                (cat_name, cat_desc)
            )

    # Check if seed products were already initialized or cleared
    cursor.execute(f"SELECT setting_value FROM settings WHERE setting_key = {placeholder}", ("seed_data_initialized",))
    if cursor.fetchone():
        return

    # 3. Seed Products with Beginning Stock
    products = [
        ("PAM-BLK-500", "Paminta Whole Black Peppercorns (500g)", "Paminta & Whole Spices", "pouch", 290.00, 170.00, 120.00, 20.00, "Sun-dried whole black peppercorns, aromatic and richly pungent.", "/assets/images/logo.jpg"),
        ("PAM-BLK-1KG", "Paminta Whole Black Peppercorns (1kg Sack)", "Paminta & Whole Spices", "kg", 550.00, 330.00, 60.00, 15.00, "Wholesale farm-grade whole black pepper in breathable woven sacks.", "/assets/images/logo.jpg"),
        ("PAM-GND-250", "Pure Ground Black Paminta (250g Jar)", "Ground & Blended Spices", "jar", 175.00, 95.00, 90.00, 15.00, "Finely ground pure black peppercorn powder with rich aroma.", "/assets/images/logo.jpg"),
        ("PAM-GND-1KG", "Pure Ground Black Paminta (1kg Commercial)", "Ground & Blended Spices", "kg", 590.00, 350.00, 40.00, 10.00, "Restaurant and kitchen commercial bulk ground black pepper.", "/assets/images/logo.jpg"),
        ("PAM-GRN-200", "Gourmet Cracked Black Paminta (200g Grinder)", "Ground & Blended Spices", "bottle", 210.00, 115.00, 75.00, 15.00, "Coarse cracked peppercorns in a refillable ceramic-burr grinder.", "/assets/images/logo.jpg"),
        ("PAM-WHT-250", "Special White Paminta Berries (250g)", "Paminta & Whole Spices", "pouch", 240.00, 135.00, 50.00, 10.00, "De-hulled ripe peppercorn berries with subtle heat and delicate aroma.", "/assets/images/logo.jpg"),
        ("WIN-CAB-750", "J&A Estate Cabernet Reserve Wine (750ml)", "Estate Wines & Cellar Reserve", "bottle", 1350.00, 720.00, 35.00, 5.00, "Oak-aged dry red wine with deep blackberry, plum, and black pepper notes.", "/assets/images/logo.jpg"),
        ("WIN-SWT-750", "J&A Vineyard Sweet Red Wine (750ml)", "Estate Wines & Cellar Reserve", "bottle", 950.00, 480.00, 40.00, 8.00, "Lush sweet red table wine bursting with vibrant ripe grape flavors.", "/assets/images/logo.jpg"),
        ("GRP-BOX-2KG", "J&A Fresh Vineyard Grapes Harvest Box (2kg)", "Fresh Harvest & Table Grapes", "box", 480.00, 220.00, 30.00, 5.00, "Crisp sweet green and dark purple table grapes freshly picked from the vine.", "/assets/images/logo.jpg"),
        ("SET-HRT-001", "J&A Paminta & Wine Heritage Gift Box", "Heritage Gift Packs", "box", 1850.00, 920.00, 25.00, 5.00, "Luxury wooden gift chest containing 1 Reserve Wine, 500g Paminta, and Grinder.", "/assets/images/logo.jpg")
    ]

    for sku, name, cat_name, unit, price, cost, beg_stock, min_alert, desc, img in products:
        cursor.execute(f"SELECT id FROM products WHERE sku = {placeholder}", (sku,))
        if not cursor.fetchone():
            # Get category id
            cursor.execute(f"SELECT id FROM categories WHERE name = {placeholder}", (cat_name,))
            cat_row = cursor.fetchone()
            cat_id = cat_row[0] if isinstance(cat_row, (tuple, list)) else (cat_row["id"] if isinstance(cat_row, dict) else 1)

            cursor.execute(
                f"""INSERT INTO products 
                (sku, name, category_id, unit, unit_price, cost_price, beginning_stock, current_stock, min_stock_alert, description, image_url) 
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})""",
                (sku, name, cat_id, unit, price, cost, beg_stock, beg_stock, min_alert, desc, img)
            )
            # Fetch inserted product id
            cursor.execute(f"SELECT id FROM products WHERE sku = {placeholder}", (sku,))
            prod_row = cursor.fetchone()
            prod_id = prod_row[0] if isinstance(prod_row, (tuple, list)) else (prod_row["id"] if isinstance(prod_row, dict) else 1)

            # Record initial BEGINNING_BALANCE movement
            cursor.execute(
                f"""INSERT INTO inventory_movements 
                (product_id, movement_type, quantity, previous_stock, new_stock, reference_id, reference_type, notes, created_by)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})""",
                (prod_id, "BEGINNING_BALANCE", beg_stock, 0.0, beg_stock, "INIT-2026", "AUDIT", "Beginning inventory setup for Jen & Albert Paminta", "admin")
            )

    # 4. Settings
    default_settings = [
        ("estate_name", "Jen & Albert Paminta"),
        ("estate_tagline", "Fine Vineyard Wines & Premium Harvest Paminta"),
        ("contact_email", "contact@jenalbertpaminta.com"),
        ("contact_phone", "+63 917 123 4567"),
        ("address", "Paminta Estate & Vineyards, Philippines"),
        ("currency_symbol", "₱"),
        ("tax_rate", "0.00"),
        ("seed_data_initialized", "true")
    ]
    for key, val in default_settings:
        cursor.execute(f"SELECT id FROM settings WHERE setting_key = {placeholder}", (key,))
        if not cursor.fetchone():
            cursor.execute(
                f"INSERT INTO settings (setting_key, setting_value) VALUES ({placeholder}, {placeholder})",
                (key, val)
            )

    if not is_mysql:
        conn.commit()

