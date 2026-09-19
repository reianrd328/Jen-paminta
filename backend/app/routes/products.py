from flask import Blueprint, request, jsonify
from app.db import DB

products_bp = Blueprint("products_bp", __name__, url_prefix="/api/products")

@products_bp.route("", methods=["GET"])
def get_products():
    category_id = request.args.get("category_id")
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "")  # 'all', 'low_stock', 'active'

    query = """
        SELECT p.*, c.name as category_name,
        CASE 
            WHEN p.current_stock <= 0 THEN 'OUT_OF_STOCK'
            WHEN p.current_stock <= p.min_stock_alert THEN 'LOW_STOCK'
            ELSE 'IN_STOCK'
        END as stock_status
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.is_active = 1
    """
    params = []

    if category_id:
        query += " AND p.category_id = %s"
        params.append(category_id)

    if search:
        query += " AND (p.name LIKE %s OR p.sku LIKE %s OR p.description LIKE %s)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term])

    if status == "low_stock":
        query += " AND p.current_stock <= p.min_stock_alert"

    query += " ORDER BY p.name ASC"

    products = DB.fetch_all(query, tuple(params) if params else None)
    return jsonify({"success": True, "products": products})

@products_bp.route("/<int:product_id>", methods=["GET"])
def get_product(product_id):
    product = DB.fetch_one("""
        SELECT p.*, c.name as category_name 
        FROM products p 
        LEFT JOIN categories c ON p.category_id = c.id 
        WHERE p.id = %s
    """, (product_id,))
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404
    return jsonify({"success": True, "product": product})

@products_bp.route("", methods=["POST"])
def create_product():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    sku = (data.get("sku") or "").strip().upper()
    category_id = data.get("category_id")
    unit = data.get("unit", "pack").strip()
    unit_price = float(data.get("unit_price") or 0.0)
    cost_price = float(data.get("cost_price") or 0.0)
    beginning_stock = float(data.get("beginning_stock") or 0.0)
    min_stock_alert = float(data.get("min_stock_alert") or 10.0)
    description = (data.get("description") or "").strip()
    image_url = (data.get("image_url") or "/assets/images/logo.jpg").strip()

    if not name:
        return jsonify({"success": False, "message": "Product name is required"}), 400

    if not sku:
        # Generate SKU from name
        import re, random
        clean = re.sub(r'[^A-Z0-9]', '', name.upper())[:4]
        sku = f"PAM-{clean}-{random.randint(100, 999)}"

    # Check duplicate SKU
    existing = DB.fetch_one("SELECT id FROM products WHERE sku = %s", (sku,))
    if existing:
        return jsonify({"success": False, "message": f"SKU '{sku}' already exists"}), 400

    res = DB.execute_query("""
        INSERT INTO products 
        (sku, name, category_id, unit, unit_price, cost_price, beginning_stock, current_stock, min_stock_alert, description, image_url, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
    """, (sku, name, category_id, unit, unit_price, cost_price, beginning_stock, beginning_stock, min_stock_alert, description, image_url), commit=True)

    product_id = res.get("last_id")

    # Record beginning balance in inventory movements ledger
    if beginning_stock > 0:
        DB.execute_query("""
            INSERT INTO inventory_movements
            (product_id, movement_type, quantity, previous_stock, new_stock, reference_id, reference_type, notes, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (product_id, "BEGINNING_BALANCE", beginning_stock, 0.0, beginning_stock, "NEW-PRODUCT", "AUDIT", "Initial beginning stock setup", "admin"), commit=True)

    return jsonify({
        "success": True, 
        "message": f"Product '{name}' created successfully with beginning stock {beginning_stock} {unit}",
        "product_id": product_id
    }), 201

@products_bp.route("/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    product = DB.fetch_one("SELECT * FROM products WHERE id = %s", (product_id,))
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404

    data = request.get_json() or {}
    name = data.get("name", product["name"]).strip()
    sku = data.get("sku", product["sku"]).strip().upper()
    category_id = data.get("category_id", product["category_id"])
    unit = data.get("unit", product["unit"]).strip()
    unit_price = float(data.get("unit_price", product["unit_price"]))
    cost_price = float(data.get("cost_price", product["cost_price"]))
    min_stock_alert = float(data.get("min_stock_alert", product["min_stock_alert"]))
    description = data.get("description", product["description"]).strip()
    image_url = data.get("image_url", product.get("image_url", "/assets/images/logo.jpg"))

    DB.execute_query("""
        UPDATE products SET 
        name = %s, sku = %s, category_id = %s, unit = %s, unit_price = %s, 
        cost_price = %s, min_stock_alert = %s, description = %s, image_url = %s
        WHERE id = %s
    """, (name, sku, category_id, unit, unit_price, cost_price, min_stock_alert, description, image_url, product_id), commit=True)

    return jsonify({"success": True, "message": "Product updated successfully"})

@products_bp.route("/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    product = DB.fetch_one("SELECT * FROM products WHERE id = %s", (product_id,))
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404

    # Soft delete by deactivating
    DB.execute_query("UPDATE products SET is_active = 0 WHERE id = %s", (product_id,), commit=True)
    return jsonify({"success": True, "message": f"Product '{product['name']}' removed from catalog"})

