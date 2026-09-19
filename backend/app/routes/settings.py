import time
from flask import Blueprint, request, jsonify
from app.db import DB

settings_bp = Blueprint("settings_bp", __name__, url_prefix="/api/settings")

@settings_bp.route("", methods=["GET"])
def get_settings():
    rows = DB.fetch_all("SELECT setting_key, setting_value FROM settings")
    settings_dict = {r["setting_key"]: r["setting_value"] for r in rows}
    return jsonify({"success": True, "settings": settings_dict})

@settings_bp.route("", methods=["POST"])
def update_settings():
    data = request.get_json() or {}
    for key, val in data.items():
        existing = DB.fetch_one("SELECT id FROM settings WHERE setting_key = %s", (key,))
        if existing:
            DB.execute_query("UPDATE settings SET setting_value = %s WHERE setting_key = %s", (str(val), key), commit=True)
        else:
            DB.execute_query("INSERT INTO settings (setting_key, setting_value) VALUES (%s, %s)", (key, str(val)), commit=True)
    return jsonify({"success": True, "message": "Settings updated successfully"})

@settings_bp.route("/health", methods=["GET"])
def get_health():
    """Live database status check for TiDB Cloud / MySQL or local database"""
    t0 = time.time()
    try:
        status_info = DB.get_status()
        latency_ms = round((time.time() - t0) * 1000, 2)
        status_info["latency_ms"] = latency_ms
        return jsonify({
            "status": "healthy",
            "database": status_info
        })
    except Exception as e:
        return jsonify({
            "status": "degraded",
            "error": str(e)
        }), 500

