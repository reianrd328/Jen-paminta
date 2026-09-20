from flask import Blueprint, request, jsonify
from app.db import DB
from datetime import date

inventory_bp = Blueprint("inventory_bp", __name__, url_prefix="/api/inventory")

@inventory_bp.route("/add-stock", methods=["POST"])
def add_stock():
    """Add / replenish stock of Paminta or other estate products (STOCK IN)"""
    data = request.get_json() or {}
    product_id = data.get("product_id")
    quantity = float(data.get("quantity") or 0.0)
    reference_id = (data.get("reference_id") or "").strip()
    reference_type = (data.get("reference_type") or "RESTOCK").strip()
    notes = (data.get("notes") or "").strip()
    cost_price = data.get("cost_price")
    created_by = (data.get("created_by") or "admin").strip()

    if not product_id or quantity <= 0:
        return jsonify({"success": False, "message": "Product ID and a positive quantity are required"}), 400

    product = DB.fetch_one("SELECT * FROM products WHERE id = %s", (product_id,))
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404

    previous_stock = float(product["current_stock"])
    new_stock = previous_stock + quantity

    # Optional cost price update
    if cost_price is not None and float(cost_price) > 0:
        new_cost = float(cost_price)
        DB.execute_query("""
            UPDATE products SET current_stock = %s, cost_price = %s WHERE id = %s
        """, (new_stock, new_cost, product_id), commit=True)
    else:
        DB.execute_query("""
            UPDATE products SET current_stock = %s WHERE id = %s
        """, (new_stock, product_id), commit=True)

    # Log movement in inventory audit ledger
    DB.execute_query("""
        INSERT INTO inventory_movements 
        (product_id, movement_type, quantity, previous_stock, new_stock, reference_id, reference_type, notes, created_by)
        VALUES (%s, 'STOCK_IN', %s, %s, %s, %s, %s, %s, %s)
    """, (product_id, quantity, previous_stock, new_stock, reference_id or "STOCK-IN", reference_type, notes or f"Added {quantity} {product['unit']} to stock", created_by), commit=True)

    return jsonify({
        "success": True,
        "message": f"Successfully added +{quantity} {product['unit']} to {product['name']}. New Stock: {new_stock} {product['unit']}",
        "product_id": product_id,
        "previous_stock": previous_stock,
        "new_stock": new_stock
    })

@inventory_bp.route("/less-stock", methods=["POST"])
def less_stock():
    """Deduct / adjust stock for damage, spoilage, shrinkage, sampling, count error (STOCK LESS)"""
    data = request.get_json() or {}
    product_id = data.get("product_id")
    quantity = float(data.get("quantity") or 0.0)
    reason = (data.get("reason") or "DAMAGE").strip().upper()
    reference_id = (data.get("reference_id") or "").strip()
    notes = (data.get("notes") or "").strip()
    created_by = (data.get("created_by") or "admin").strip()

    if not product_id or quantity <= 0:
        return jsonify({"success": False, "message": "Product ID and a positive deduction quantity are required"}), 400

    product = DB.fetch_one("SELECT * FROM products WHERE id = %s", (product_id,))
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404

    previous_stock = float(product["current_stock"])
    if previous_stock < quantity:
        return jsonify({
            "success": False, 
            "message": f"Insufficient stock to deduct {quantity} {product['unit']}. Current stock is only {previous_stock} {product['unit']}"
        }), 400

    new_stock = previous_stock - quantity

    DB.execute_query("""
        UPDATE products SET current_stock = %s WHERE id = %s
    """, (new_stock, product_id), commit=True)

    # Log movement in inventory audit ledger
    DB.execute_query("""
        INSERT INTO inventory_movements 
        (product_id, movement_type, quantity, previous_stock, new_stock, reference_id, reference_type, notes, created_by)
        VALUES (%s, 'ADJUSTMENT_LESS', %s, %s, %s, %s, %s, %s, %s)
    """, (product_id, quantity, previous_stock, new_stock, reference_id or "LESS-ADJ", reason, notes or f"Deducted {quantity} {product['unit']} ({reason})", created_by), commit=True)

    return jsonify({
        "success": True,
        "message": f"Successfully deducted -{quantity} {product['unit']} from {product['name']}. New Stock: {new_stock} {product['unit']}",
        "product_id": product_id,
        "previous_stock": previous_stock,
        "new_stock": new_stock
    })

@inventory_bp.route("/set-beginning-stock", methods=["POST"])
def set_beginning_stock():
    """Establish or reset the Beginning Inventory for a product"""
    data = request.get_json() or {}
    product_id = data.get("product_id")
    beginning_stock = float(data.get("beginning_stock") or 0.0)
    notes = (data.get("notes") or "").strip()

    if not product_id or beginning_stock < 0:
        return jsonify({"success": False, "message": "Valid product ID and beginning stock are required"}), 400

    product = DB.fetch_one("SELECT * FROM products WHERE id = %s", (product_id,))
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404

    # Calculate difference
    old_beginning = float(product["beginning_stock"])
    diff = beginning_stock - old_beginning
    new_current = float(product["current_stock"]) + diff

    DB.execute_query("""
        UPDATE products SET beginning_stock = %s, current_stock = %s WHERE id = %s
    """, (beginning_stock, new_current, product_id), commit=True)

    DB.execute_query("""
        INSERT INTO inventory_movements 
        (product_id, movement_type, quantity, previous_stock, new_stock, reference_id, reference_type, notes, created_by)
        VALUES (%s, 'BEGINNING_BALANCE', %s, %s, %s, %s, 'AUDIT', %s, 'admin')
    """, (product_id, beginning_stock, product["current_stock"], new_current, "SET-BEG-BAL", notes or f"Beginning stock set to {beginning_stock} {product['unit']}"), commit=True)

    return jsonify({
        "success": True,
        "message": f"Beginning stock for {product['name']} set to {beginning_stock} {product['unit']}. Current Stock: {new_current}",
        "beginning_stock": beginning_stock,
        "current_stock": new_current
    })

@inventory_bp.route("/ledger", methods=["GET"])
def get_inventory_ledger():
    """
    Master Beginning & Ending Inventory Reconciliation Ledger.
    Formula: Ending = Beginning + Stock In - Sales Deductions - Less Adjustments
    """
    category_id = request.args.get("category_id")
    search = request.args.get("search", "").strip()

    # Query all active products
    query = """
        SELECT p.id, p.sku, p.name, p.unit, p.unit_price, p.cost_price, 
               p.beginning_stock, p.current_stock, p.min_stock_alert,
               p.image_url,
               c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.is_active = 1
    """
    params = []
    if category_id:
        query += " AND p.category_id = %s"
        params.append(category_id)
    if search:
        query += " AND (p.name LIKE %s OR p.sku LIKE %s)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term])

    query += " ORDER BY c.name ASC, p.name ASC"
    products = DB.fetch_all(query, tuple(params) if params else None)

    # Fetch movement totals per product
    movements_summary = DB.fetch_all("""
        SELECT product_id, movement_type, SUM(quantity) as total_qty
        FROM inventory_movements
        GROUP BY product_id, movement_type
    """)

    # Map totals by product_id
    mov_map = {}
    for m in movements_summary:
        pid = m["product_id"]
        mtype = m["movement_type"]
        if pid not in mov_map:
            mov_map[pid] = {"STOCK_IN": 0.0, "SALE_DEDUCTION": 0.0, "ADJUSTMENT_LESS": 0.0, "ADJUSTMENT_ADD": 0.0}
        mov_map[pid][mtype] = float(m["total_qty"])

    ledger_items = []
    grand_totals = {
        "total_beginning_value": 0.0,
        "total_ending_value": 0.0,
        "total_retail_value": 0.0,
        "total_items_count": len(products),
        "low_stock_count": 0,
        "out_of_stock_count": 0
    }

    for p in products:
        pid = p["id"]
        p_mov = mov_map.get(pid, {"STOCK_IN": 0.0, "SALE_DEDUCTION": 0.0, "ADJUSTMENT_LESS": 0.0, "ADJUSTMENT_ADD": 0.0})

        beginning = float(p["beginning_stock"])
        added = float(p_mov.get("STOCK_IN", 0.0) + p_mov.get("ADJUSTMENT_ADD", 0.0))
        sales_out = float(p_mov.get("SALE_DEDUCTION", 0.0))
        less_out = float(p_mov.get("ADJUSTMENT_LESS", 0.0))
        current = float(p["current_stock"])
        calculated_ending = beginning + added - sales_out - less_out

        cost = float(p["cost_price"])
        price = float(p["unit_price"])
        min_alert = float(p["min_stock_alert"])

        ending_value = current * cost
        retail_value = current * price
        beginning_value = beginning * cost

        status = "IN_STOCK"
        if current <= 0:
            status = "OUT_OF_STOCK"
            grand_totals["out_of_stock_count"] += 1
        elif current <= min_alert:
            status = "LOW_STOCK"
            grand_totals["low_stock_count"] += 1

        grand_totals["total_beginning_value"] += beginning_value
        grand_totals["total_ending_value"] += ending_value
        grand_totals["total_retail_value"] += retail_value

        ledger_items.append({
            "product_id": pid,
            "sku": p["sku"],
            "name": p["name"],
            "image_url": p.get("image_url") or "/logo.jpg",
            "category_name": p["category_name"] or "General",
            "unit": p["unit"],
            "unit_price": price,
            "cost_price": cost,
            "beginning_stock": round(beginning, 2),
            "stock_added": round(added, 2),
            "sales_deducted": round(sales_out, 2),
            "less_adjustments": round(less_out, 2),
            "calculated_ending": round(calculated_ending, 2),
            "current_stock": round(current, 2),
            "variance": round(current - calculated_ending, 2),
            "inventory_value": round(ending_value, 2),
            "retail_value": round(retail_value, 2),
            "min_stock_alert": min_alert,
            "status": status
        })

    return jsonify({
        "success": True,
        "ledger": ledger_items,
        "summary": grand_totals
    })

@inventory_bp.route("/movements", methods=["GET"])
def get_movements():
    """Audit log of all stock movements (In, Less, Sale deductions, Beginning setup)"""
    product_id = request.args.get("product_id")
    movement_type = request.args.get("movement_type")
    limit = int(request.args.get("limit", 100))

    query = """
        SELECT m.*, p.name as product_name, p.sku, p.unit 
        FROM inventory_movements m
        JOIN products p ON m.product_id = p.id
        WHERE 1=1
    """
    params = []
    if product_id:
        query += " AND m.product_id = %s"
        params.append(product_id)
    if movement_type:
        query += " AND m.movement_type = %s"
        params.append(movement_type)

    query += " ORDER BY m.created_at DESC, m.id DESC LIMIT %s"
    params.append(limit)

    movements = DB.fetch_all(query, tuple(params))
    return jsonify({"success": True, "movements": movements})

@inventory_bp.route("/reset-records", methods=["POST"])
def reset_records():
    """
    Clears all products, inventory movements, inventory snapshots, sales, and sale items.
    Leaves user accounts, categories, and settings intact.
    Marks seed_data_initialized = 'true' so demo products won't return.
    """
    DB.execute_query("DELETE FROM sale_items", commit=True)
    DB.execute_query("DELETE FROM sales", commit=True)
    DB.execute_query("DELETE FROM inventory_movements", commit=True)
    DB.execute_query("DELETE FROM inventory_snapshots", commit=True)
    DB.execute_query("DELETE FROM products", commit=True)

    # Ensure seed_data_initialized is set
    existing = DB.fetch_one("SELECT id FROM settings WHERE setting_key = %s", ("seed_data_initialized",))
    if existing:
        DB.execute_query("UPDATE settings SET setting_value = 'true' WHERE setting_key = %s", ("seed_data_initialized",), commit=True)
    else:
        DB.execute_query("INSERT INTO settings (setting_key, setting_value) VALUES (%s, 'true')", ("seed_data_initialized",), commit=True)

    return jsonify({
        "success": True,
        "message": "All product records, stock movements, and sales history have been cleared. You now have a clean slate to add your stock!"
    })


