import sys
import os

# Set utf-8 encoding for standard output
sys.stdout.reconfigure(encoding='utf-8')

# Set path
sys.path.insert(0, os.path.abspath("backend"))

from app import create_app
from app.db import DB, init_db

def run_tests():
    print("==================================================================")
    print("  RUNNING AUTOMATED TESTS FOR JEN & ALBERT PAMINTA SYSTEM")
    print("==================================================================")
    
    app = create_app()
    client = app.test_client()

    # 1. Test Health Endpoint
    print("\n[1] Testing /api/settings/health ...")
    res = client.get("/api/settings/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    health_data = res.get_json()
    print(f"  --> Status: {health_data['status']}")
    print(f"  --> Engine: {health_data['database']['engine']}")
    print(f"  --> Host:   {health_data['database']['host']}")

    # 2. Test Products Listing
    print("\n[2] Testing /api/products (Catalog & Beginning Stocks) ...")
    res = client.get("/api/products")
    assert res.status_code == 200
    prods = res.get_json()["products"]
    print(f"  --> Total Seeded Products: {len(prods)}")
    paminta_1kg = next((p for p in prods if p["sku"] == "PAM-BLK-1KG"), None)
    assert paminta_1kg is not None, "PAM-BLK-1KG not found!"
    initial_beg = float(paminta_1kg["beginning_stock"])
    initial_curr = float(paminta_1kg["current_stock"])
    print(f"  --> Tested Product: {paminta_1kg['name']}")
    print(f"      Initial Beginning Stock: {initial_beg} {paminta_1kg['unit']}")
    print(f"      Initial Current Stock:   {initial_curr} {paminta_1kg['unit']}")

    # 3. Test Add Stock (+ Restock of Paminta)
    print("\n[3] Testing /api/inventory/add-stock (+50 kg Paminta) ...")
    add_qty = 50.0
    res = client.post("/api/inventory/add-stock", json={
        "product_id": paminta_1kg["id"],
        "quantity": add_qty,
        "reference_id": "HARVEST-BATCH-TEST-01",
        "notes": "Farm delivery test addition"
    })
    assert res.status_code == 200, f"Add stock failed: {res.get_json()}"
    add_data = res.get_json()
    print(f"  --> Result: {add_data['message']}")
    expected_after_add = initial_curr + add_qty
    assert float(add_data["new_stock"]) == expected_after_add, f"Expected {expected_after_add}, got {add_data['new_stock']}"

    # 4. Test Less Stock (- Deduct Spoilage/Damage)
    print("\n[4] Testing /api/inventory/less-stock (-5 kg Paminta Damage) ...")
    less_qty = 5.0
    res = client.post("/api/inventory/less-stock", json={
        "product_id": paminta_1kg["id"],
        "quantity": less_qty,
        "reason": "DAMAGE",
        "reference_id": "ADJ-TEST-001",
        "notes": "Moisture exposure during transport"
    })
    assert res.status_code == 200, f"Less stock failed: {res.get_json()}"
    less_data = res.get_json()
    print(f"  --> Result: {less_data['message']}")
    expected_after_less = expected_after_add - less_qty
    assert float(less_data["new_stock"]) == expected_after_less, f"Expected {expected_after_less}, got {less_data['new_stock']}"

    # 5. Test Sales Module Connected to Inventory (Automatic Stock Deduction)
    print("\n[5] Testing /api/sales (POS Sale Checkout: Sell 10 kg Paminta) ...")
    sale_qty = 10.0
    res = client.post("/api/sales", json={
        "customer_name": "Don Juan Restaurant",
        "customer_contact": "09181112233",
        "payment_method": "CASH",
        "amount_tendered": 6000.00,
        "discount": 100.00,
        "notes": "Bulk order of whole black paminta",
        "items": [
            {
                "product_id": paminta_1kg["id"],
                "quantity": sale_qty,
                "unit_price": float(paminta_1kg["unit_price"])
            }
        ]
    })
    assert res.status_code == 201, f"Sale checkout failed: {res.get_json()}"
    sale_data = res.get_json()["sale"]
    invoice_num = sale_data["invoice_number"]
    print(f"  --> Invoice Generated: {invoice_num}")
    print(f"  --> Total Amount:      PHP {sale_data['total_amount']:.2f}")
    print(f"  --> Change Due:        PHP {sale_data['change_due']:.2f}")
    
    # Check item stock after sale deduction
    sold_item = sale_data["items"][0]
    expected_after_sale = expected_after_less - sale_qty
    print(f"  --> Stock After Sale:  {sold_item['new_stock']} {paminta_1kg['unit']} (Expected: {expected_after_sale})")
    assert float(sold_item["new_stock"]) == expected_after_sale, f"Stock deduction mismatch!"

    # 6. Test Inventory Reconciliation Ledger
    print("\n[6] Testing /api/inventory/ledger (Beginning vs Ending Formula) ...")
    res = client.get("/api/inventory/ledger")
    assert res.status_code == 200
    ledger = res.get_json()["ledger"]
    item_ledger = next((it for it in ledger if it["product_id"] == paminta_1kg["id"]), None)
    assert item_ledger is not None
    print(f"  --> Item:              {item_ledger['name']}")
    print(f"      Beginning Stock:   {item_ledger['beginning_stock']}")
    print(f"      + Stock Added:     {item_ledger['stock_added']}")
    print(f"      - Sales Deducted:  {item_ledger['sales_deducted']}")
    print(f"      - Less Adj:        {item_ledger['less_adjustments']}")
    print(f"      Calculated Ending: {item_ledger['calculated_ending']}")
    print(f"      Current Stock:     {item_ledger['current_stock']}")
    print(f"      Variance:          {item_ledger['variance']}")
    
    assert item_ledger["variance"] == 0.0, f"Variance must be 0! Got {item_ledger['variance']}"
    assert item_ledger["current_stock"] == item_ledger["calculated_ending"], "Ending stock formula mismatch!"

    # 7. Test Dashboard Stats
    print("\n[7] Testing /api/dashboard/stats ...")
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    dash_data = res.get_json()
    k = dash_data["kpis"]
    print(f"  --> Today's Sales:     PHP {k['today_sales']:.2f}")
    print(f"  --> Ending Valuation:  PHP {k['ending_inventory_value']:.2f}")
    print(f"  --> Low Stock Items:   {k['low_stock_count']}")

    # 8. Test Frontend Route Serving
    print("\n[8] Testing Frontend Page Routes ...")
    r_home = client.get("/")
    assert r_home.status_code == 200
    assert b"JEN & ALBERT" in r_home.data
    print("  --> Public Home Page (/) OK")

    r_admin = client.get("/admin")
    assert r_admin.status_code == 200
    assert b"Master Inventory & Reconciliation Ledger" in r_admin.data
    print("  --> Admin Portal (/admin) OK")

    r_login = client.get("/login")
    assert r_login.status_code == 200
    assert b"Staff & Inventory Access Portal" in r_login.data
    print("  --> Staff Login (/login) OK")

    r_logo = client.get("/logo.jpg")
    assert r_logo.status_code == 200
    assert len(r_logo.data) > 10000
    print(f"  --> Logo Served (/logo.jpg) OK ({len(r_logo.data)} bytes)")

    print("\n==================================================================")
    print("  SUCCESS: ALL TESTS PASSED! SYSTEM VERIFIED 100% OPERATIONAL")
    print("==================================================================")

if __name__ == "__main__":
    run_tests()
