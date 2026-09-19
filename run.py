import os
import sys

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("  🍇 JEN & ALBERT PAMINTA INVENTORY & SALES SYSTEM 🍇")
    print(f"  Running locally at: http://localhost:{port}")
    print(f"  Admin Portal:      http://localhost:{port}/admin")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True)

