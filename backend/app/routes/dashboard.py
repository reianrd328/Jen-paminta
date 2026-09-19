from datetime import datetime, date, timedelta
from flask import Blueprint, jsonify
from app.db import DB

dashboard_bp = Blueprint("dashboard_bp", __name__, url_prefix="/api/dashboard")

@dashboard_bp.route("/stats", methods=["GET"])
def get_stats():
    today_str = date.today().strftime("%Y-%m-%d")
    month_str = date.today().strftime("%Y-%m")

    # 1. Today's Sales
    today_sales_res = DB.fetch_one("""
        SELECT COALESCE(SUM(total_amount), 0) as total, COUNT(id) as count
        FROM sales 
        WHERE status = 'COMPLETED' AND created_at LIKE %s
    """, (f"{today_str}%",))

    # 2. Month's Sales
    month_sales_res = DB.fetch_one("""
        SELECT COALESCE(SUM(total_amount), 0) as total, COUNT(id) as count
        FROM sales 
        WHERE status = 'COMPLETED' AND created_at LIKE %s
    """, (f"{month_str}%",))

    # 3. Products & Stock Metrics
    prods = DB.fetch_all("""
        SELECT id, name, sku, unit, beginning_stock, current_stock, min_stock_alert, cost_price, unit_price
        FROM products 
        WHERE is_active = 1
    """)

    total_beginning_val = 0.0
    total_ending_val = 0.0
    total_retail_val = 0.0
    low_stock_items = []

    for p in prods:
        beg = float(p["beginning_stock"])
        curr = float(p["current_stock"])
        cost = float(p["cost_price"])
        price = float(p["unit_price"])
        min_alt = float(p["min_stock_alert"])

        total_beginning_val += beg * cost
        total_ending_val += curr * cost
        total_retail_val += curr * price

        if curr <= min_alt:
            low_stock_items.append({
                "id": p["id"],
                "sku": p["sku"],
                "name": p["name"],
                "unit": p["unit"],
                "current_stock": curr,
                "min_stock_alert": min_alt,
                "is_empty": curr <= 0
            })

    # 4. Top Selling Products
    top_selling = DB.fetch_all("""
        SELECT si.product_name, si.unit, SUM(si.quantity) as total_qty, SUM(si.subtotal) as total_revenue
        FROM sale_items si
        JOIN sales s ON si.sale_id = s.id
        WHERE s.status = 'COMPLETED'
        GROUP BY si.product_id, si.product_name, si.unit
        ORDER BY total_qty DESC
        LIMIT 5
    """)

    # 5. Recent 7 Days Sales Trend
    seven_days_data = []
    for i in range(6, -1, -1):
        day = (date.today() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_sales = DB.fetch_one("""
            SELECT COALESCE(SUM(total_amount), 0) as total, COUNT(id) as count
            FROM sales 
            WHERE status = 'COMPLETED' AND created_at LIKE %s
        """, (f"{day}%",))
        seven_days_data.append({
            "date": day,
            "label": (date.today() - timedelta(days=i)).strftime("%b %d"),
            "total": float(day_sales["total"]) if day_sales else 0.0,
            "orders": int(day_sales["count"]) if day_sales else 0
        })

    # 6. Recent Sales
    recent_sales = DB.fetch_all("""
        SELECT id, invoice_number, customer_name, total_amount, payment_method, status, created_at
        FROM sales
        ORDER BY created_at DESC, id DESC
        LIMIT 5
    """)

    # 7. Recent Movements
    recent_movements = DB.fetch_all("""
        SELECT m.*, p.name as product_name, p.unit
        FROM inventory_movements m
        JOIN products p ON m.product_id = p.id
        ORDER BY m.created_at DESC, m.id DESC
        LIMIT 8
    """)

    return jsonify({
        "success": True,
        "kpis": {
            "today_sales": float(today_sales_res["total"]) if today_sales_res else 0.0,
            "today_orders": int(today_sales_res["count"]) if today_sales_res else 0,
            "month_sales": float(month_sales_res["total"]) if month_sales_res else 0.0,
            "month_orders": int(month_sales_res["count"]) if month_sales_res else 0,
            "total_products": len(prods),
            "low_stock_count": len(low_stock_items),
            "beginning_inventory_value": round(total_beginning_val, 2),
            "ending_inventory_value": round(total_ending_val, 2),
            "estimated_retail_value": round(total_retail_val, 2)
        },
        "low_stock_alerts": low_stock_items,
        "top_selling": top_selling,
        "chart_data": seven_days_data,
        "recent_sales": recent_sales,
        "recent_movements": recent_movements
    })

