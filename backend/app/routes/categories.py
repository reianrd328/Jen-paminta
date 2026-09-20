from flask import Blueprint, request, jsonify
from app.db import DB

categories_bp = Blueprint("categories_bp", __name__, url_prefix="/api/categories")

@categories_bp.route("", methods=["GET"])
def get_categories():
    """Fetch all product categories with associated active product count"""
    query = """
        SELECT c.id, c.name, c.description, c.created_at,
               COUNT(p.id) as product_count
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id AND p.is_active = 1
        GROUP BY c.id, c.name, c.description, c.created_at
        ORDER BY c.name ASC
    """
    categories = DB.fetch_all(query)
    return jsonify({"success": True, "categories": categories})

@categories_bp.route("/<int:category_id>", methods=["GET"])
def get_category(category_id):
    category = DB.fetch_one("SELECT * FROM categories WHERE id = %s", (category_id,))
    if not category:
        return jsonify({"success": False, "message": "Category not found"}), 404
    return jsonify({"success": True, "category": category})

@categories_bp.route("", methods=["POST"])
def create_category():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()

    if not name:
        return jsonify({"success": False, "message": "Category name is required"}), 400

    # Check case-insensitive duplicate
    existing = DB.fetch_one("SELECT id, name FROM categories WHERE LOWER(name) = LOWER(%s)", (name,))
    if existing:
        return jsonify({
            "success": True,
            "message": f"Category '{existing['name']}' already exists",
            "category_id": existing["id"],
            "category": existing
        }), 200

    res = DB.execute_query("""
        INSERT INTO categories (name, description) VALUES (%s, %s)
    """, (name, description), commit=True)

    category_id = res.get("last_id")
    new_cat = DB.fetch_one("SELECT * FROM categories WHERE id = %s", (category_id,))

    return jsonify({
        "success": True,
        "message": f"Custom category '{name}' created successfully",
        "category_id": category_id,
        "category": new_cat
    }), 201

@categories_bp.route("/<int:category_id>", methods=["PUT"])
def update_category(category_id):
    category = DB.fetch_one("SELECT * FROM categories WHERE id = %s", (category_id,))
    if not category:
        return jsonify({"success": False, "message": "Category not found"}), 404

    data = request.get_json() or {}
    name = (data.get("name") or category["name"]).strip()
    description = (data.get("description") or category.get("description") or "").strip()

    if not name:
        return jsonify({"success": False, "message": "Category name cannot be empty"}), 400

    # Check duplicate
    existing = DB.fetch_one("SELECT id FROM categories WHERE LOWER(name) = LOWER(%s) AND id != %s", (name, category_id))
    if existing:
        return jsonify({"success": False, "message": f"Another category named '{name}' already exists"}), 400

    DB.execute_query("""
        UPDATE categories SET name = %s, description = %s WHERE id = %s
    """, (name, description, category_id), commit=True)

    return jsonify({"success": True, "message": f"Category updated to '{name}'"})

@categories_bp.route("/<int:category_id>", methods=["DELETE"])
def delete_category(category_id):
    category = DB.fetch_one("SELECT * FROM categories WHERE id = %s", (category_id,))
    if not category:
        return jsonify({"success": False, "message": "Category not found"}), 404

    # Check products using this category
    prods = DB.fetch_all("SELECT id, name FROM products WHERE category_id = %s AND is_active = 1", (category_id,))
    if prods:
        return jsonify({
            "success": False, 
            "message": f"Cannot delete '{category['name']}' because {len(prods)} active products are assigned to it. Reassign those products first."
        }), 400

    DB.execute_query("DELETE FROM categories WHERE id = %s", (category_id,), commit=True)
    return jsonify({"success": True, "message": f"Category '{category['name']}' deleted successfully"})

