import random
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.db import DB

sales_bp = Blueprint("sales_bp", __name__, url_prefix="/api/sales")

def generate_invoice_number():
    date_str = datetime.now().strftime("%Y%m%d")
    rand_num = random.randint(1000, 9999)
    return f"INV-PAM-{date_str}-{rand_num}"

@sales_bp.route("", methods=["POST"])
def create_sale():
    """
    Process a sale (POS or Online Order) and automatically DEDUCT / LESS stock from inventory.
    Records inventory_movements as 'SALE_DEDUCTION'.
    """
    data = request.get_json() or {}
    items = data.get("items") or []
    customer_name = (data.get("customer_name") or "Walk-in Customer").strip()
    customer_contact = (data.get("customer_contact") or "").strip()
    payment_method = (data.get("payment_method") or "CASH").strip().upper()
    discount = float(data.get("discount") or 0.0)
    tax = float(data.get("tax") or 0.0)
    amount_tendered = float(data.get("amount_tendered") or 0.0)
    notes = (data.get("notes") or "").strip()
    created_by = (data.get("created_by") or "staff").strip()

    if not items:
        return jsonify({"success": False, "message": "Sale must contain at least one item"}), 400

    # 1. First Pass: Validate stock availability for all items
    items_to_process = []
    subtotal = 0.0

    for it in items:
        product_id = it.get("product_id")
        qty = float(it.get("quantity") or 0.0)
        if not product_id or qty <= 0:
            return jsonify({"success": False, "message": "Invalid item or quantity"}), 400

        product = DB.fetch_one("SELECT * FROM products WHERE id = %s AND is_active = 1", (product_id,))
        if not product:
            return jsonify({"success": False, "message": f"Product ID {product_id} not found"}), 404

        current_stock = float(product["current_stock"])
        if current_stock < qty:
            return jsonify({
                "success": False,
                "message": f"Insufficient stock for '{product['name']}'. Available: {current_stock} {product['unit']}, Requested: {qty} {product['unit']}."
            }), 400

        unit_price = float(it.get("unit_price") if it.get("unit_price") is not None else product["unit_price"])
        cost_price = float(product["cost_price"])
        item_subtotal = round(unit_price * qty, 2)
        subtotal += item_subtotal

        items_to_process.append({
            "product": product,
            "quantity": qty,
            "unit_price": unit_price,
            "cost_price": cost_price,
            "subtotal": item_subtotal,
            "current_stock": current_stock
        })

    total_amount = max(0.0, subtotal - discount + tax)
    if payment_method == "CASH" and amount_tendered < total_amount and amount_tendered > 0:
        return jsonify({
            "success": False,
            "message": f"Tendered cash ({amount_tendered:.2f}) is less than total amount ({total_amount:.2f})"
        }), 400

    change_due = max(0.0, amount_tendered - total_amount) if payment_method == "CASH" and amount_tendered > 0 else 0.0
    invoice_number = generate_invoice_number()

    # 2. Insert Sale Record
    sale_res = DB.execute_query("""
        INSERT INTO sales 
        (invoice_number, customer_name, customer_contact, subtotal, discount, tax, total_amount, payment_method, amount_tendered, change_due, status, notes, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'COMPLETED', %s, %s)
    """, (invoice_number, customer_name, customer_contact, subtotal, discount, tax, total_amount, payment_method, amount_tendered, change_due, notes, created_by), commit=True)

    sale_id = sale_res.get("last_id")

    # 3. Second Pass: Insert Sale Items AND DEDUCT inventory with audit logs
    processed_items_summary = []
    for it in items_to_process:
        prod = it["product"]
        qty = it["quantity"]
        prev_stock = it["current_stock"]
        new_stock = prev_stock - qty

        # Insert sale item
        DB.execute_query("""
            INSERT INTO sale_items 
            (sale_id, product_id, product_name, unit, unit_price, cost_price, quantity, subtotal)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (sale_id, prod["id"], prod["name"], prod["unit"], it["unit_price"], it["cost_price"], qty, it["subtotal"]), commit=True)

        # Update current stock in products table
        DB.execute_query("""
            UPDATE products SET current_stock = %s WHERE id = %s
        """, (new_stock, prod["id"]), commit=True)

        # Record stock deduction in inventory movements
        DB.execute_query("""
            INSERT INTO inventory_movements 
            (product_id, movement_type, quantity, previous_stock, new_stock, reference_id, reference_type, notes, created_by)
            VALUES (%s, 'SALE_DEDUCTION', %s, %s, %s, %s, 'SALE', %s, %s)
        """, (prod["id"], qty, prev_stock, new_stock, invoice_number, f"Sold {qty} {prod['unit']} to {customer_name}", created_by), commit=True)

        processed_items_summary.append({
            "product_id": prod["id"],
            "name": prod["name"],
            "unit": prod["unit"],
            "quantity": qty,
            "unit_price": it["unit_price"],
            "subtotal": it["subtotal"],
            "new_stock": new_stock
        })

    return jsonify({
        "success": True,
        "message": f"Sale completed! Stock updated and deducted for {len(items_to_process)} item(s).",
        "sale": {
            "id": sale_id,
            "invoice_number": invoice_number,
            "customer_name": customer_name,
            "customer_contact": customer_contact,
            "subtotal": round(subtotal, 2),
            "discount": round(discount, 2),
            "tax": round(tax, 2),
            "total_amount": round(total_amount, 2),
            "payment_method": payment_method,
            "amount_tendered": round(amount_tendered, 2),
            "change_due": round(change_due, 2),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": processed_items_summary
        }
    }), 201

@sales_bp.route("", methods=["GET"])
def get_sales():
    """List sales transactions with date filters"""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    payment_method = request.args.get("payment_method")
    status = request.args.get("status")
    limit = int(request.args.get("limit", 100))

    query = "SELECT * FROM sales WHERE 1=1"
    params = []

    if start_date:
        query += " AND created_at >= %s"
        params.append(f"{start_date} 00:00:00")
    if end_date:
        query += " AND created_at <= %s"
        params.append(f"{end_date} 23:59:59")
    if payment_method:
        query += " AND payment_method = %s"
        params.append(payment_method)
    if status:
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY created_at DESC, id DESC LIMIT %s"
    params.append(limit)

    sales = DB.fetch_all(query, tuple(params))
    return jsonify({"success": True, "sales": sales})

@sales_bp.route("/<int:sale_id>", methods=["GET"])
def get_sale_details(sale_id):
    """Get single sale with all item line records"""
    sale = DB.fetch_one("SELECT * FROM sales WHERE id = %s", (sale_id,))
    if not sale:
        return jsonify({"success": False, "message": "Sale not found"}), 404

    items = DB.fetch_all("SELECT * FROM sale_items WHERE sale_id = %s", (sale_id,))
    return jsonify({
        "success": True,
        "sale": sale,
        "items": items
    })

@sales_bp.route("/invoice/<string:invoice_num>", methods=["GET"])
def get_invoice_by_num(invoice_num):
    """Lookup invoice by invoice number"""
    sale = DB.fetch_one("SELECT * FROM sales WHERE invoice_number = %s", (invoice_num,))
    if not sale:
        return jsonify({"success": False, "message": "Invoice not found"}), 404

    items = DB.fetch_all("SELECT * FROM sale_items WHERE sale_id = %s", (sale["id"],))
    return jsonify({
        "success": True,
        "sale": sale,
        "items": items
    })

@sales_bp.route("/<int:sale_id>/void", methods=["POST"])
def void_sale(sale_id):
    """Cancel / void a sale and restore stock back to inventory"""
    sale = DB.fetch_one("SELECT * FROM sales WHERE id = %s", (sale_id,))
    if not sale:
        return jsonify({"success": False, "message": "Sale not found"}), 404

    if sale["status"] == "CANCELLED":
        return jsonify({"success": False, "message": "Sale is already cancelled"}), 400

    items = DB.fetch_all("SELECT * FROM sale_items WHERE sale_id = %s", (sale_id,))

    # Restock each product
    for it in items:
        prod_id = it["product_id"]
        qty = float(it["quantity"])
        prod = DB.fetch_one("SELECT * FROM products WHERE id = %s", (prod_id,))
        if prod:
            prev_stock = float(prod["current_stock"])
            new_stock = prev_stock + qty
            DB.execute_query("UPDATE products SET current_stock = %s WHERE id = %s", (new_stock, prod_id), commit=True)
            DB.execute_query("""
                INSERT INTO inventory_movements 
                (product_id, movement_type, quantity, previous_stock, new_stock, reference_id, reference_type, notes, created_by)
                VALUES (%s, 'ADJUSTMENT_ADD', %s, %s, %s, %s, 'VOID_RESTOCK', %s, 'admin')
            """, (prod_id, qty, prev_stock, new_stock, sale["invoice_number"], f"Restocked from voided sale {sale['invoice_number']}"), commit=True)

    DB.execute_query("UPDATE sales SET status = 'CANCELLED' WHERE id = %s", (sale_id,), commit=True)

    return jsonify({
        "success": True,
        "message": f"Sale {sale['invoice_number']} cancelled and {len(items)} product items restocked back to inventory."
    })

