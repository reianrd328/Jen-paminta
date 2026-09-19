import hashlib
from flask import Blueprint, request, jsonify, session
from app.db import DB
from app.config import Config

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required"}), 400

    pwd_hash = hash_password(password)

    user = DB.fetch_one(
        "SELECT id, username, full_name, role FROM users WHERE username = %s AND password_hash = %s",
        (username, pwd_hash)
    )

    # Fallback check with config default credentials if user table empty or mismatch
    if not user and username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
        user = {
            "id": 1,
            "username": Config.ADMIN_USERNAME,
            "full_name": "Jen & Albert Paminta Estate Admin",
            "role": "admin"
        }

    if not user:
        return jsonify({"success": False, "message": "Invalid username or password"}), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session["full_name"] = user["full_name"]

    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": user
    })

@auth_bp.route("/me", methods=["GET"])
def me():
    if "user_id" in session:
        return jsonify({
            "authenticated": True,
            "user": {
                "id": session.get("user_id"),
                "username": session.get("username"),
                "role": session.get("role"),
                "full_name": session.get("full_name")
            }
        })
    return jsonify({"authenticated": False, "user": None})

@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})

