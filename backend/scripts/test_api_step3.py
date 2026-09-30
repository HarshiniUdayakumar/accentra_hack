"""Test script for Step 3: New Transaction API and automatic customer history retrieval."""
import json
import os
import sys
import time
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.database import get_cursor

BASE_URL = "http://127.0.0.1:8000"


def send_post(endpoint: str, payload: dict):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            status_code = resp.status
            response_data = json.loads(resp.read().decode("utf-8"))
            return status_code, response_data
    except urllib.error.HTTPError as e:
        status_code = e.code
        err_body = json.loads(e.read().decode("utf-8"))
        return status_code, err_body


def main():
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    time.sleep(1)
    print("=== STEP 3: API VERIFICATION ===")

    # Check root & docs
    try:
        with urllib.request.urlopen(f"{BASE_URL}/docs") as resp:
            print(f"1. GET /docs: HTTP {resp.status} OK")
    except Exception as e:
        print(f"1. GET /docs failed: {e}")

    # Count rows before test
    with get_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS cnt FROM transactions;")
        count_before = cursor.fetchone()["cnt"]

    # Test 1: POST /api/transactions with C101
    payload_c101 = {
        "transaction_id": "TX_NEW_001",
        "customer_id": "C101",
        "amount": 90000,
        "timestamp": "2026-09-30T10:20:00",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "location_name": "Delhi",
        "merchant": "Demo Store",
        "transaction_type": "PURCHASE",
        "channel": "UPI",
    }

    status, resp = send_post("/api/transactions", payload_c101)
    print(f"\n2. Test C101 (Known Customer) -> HTTP {status}")
    print(f"   Message: {resp.get('message')}")
    print(f"   Transaction ID: {resp.get('transaction', {}).get('transaction_id')}")
    print(f"   Customer ID: {resp.get('customer_history', {}).get('customer_id')}")
    print(f"   History Count: {resp.get('customer_history', {}).get('transaction_count')}")

    history_sample = resp.get("customer_history", {}).get("transactions", [])[:3]
    print(f"   Sample Historical Records ({len(history_sample)} shown):")
    for t in history_sample:
        print(f"     - {t.get('transaction_id')}: Rs.{t.get('amount')} at {t.get('location_name')} ({t.get('timestamp')}) via {t.get('channel')}")

    # Test 2: POST /api/transactions with unknown customer C999
    payload_c999 = {
        "transaction_id": "TX_NEW_002",
        "customer_id": "C999",
        "amount": 1500,
        "timestamp": "2026-09-30T10:25:00",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "location_name": "Chennai",
        "merchant": "New Merchant",
        "transaction_type": "PAYMENT",
        "channel": "UPI",
    }

    status_c999, resp_c999 = send_post("/api/transactions", payload_c999)
    print(f"\n3. Test C999 (Unknown Customer) -> HTTP {status_c999}")
    print(f"   Message: {resp_c999.get('message')}")
    print(f"   Customer ID: {resp_c999.get('customer_history', {}).get('customer_id')}")
    print(f"   History Count: {resp_c999.get('customer_history', {}).get('transaction_count')}")
    print(f"   History List: {resp_c999.get('customer_history', {}).get('transactions')}")

    # Test 3: Validation Error Handling
    payload_invalid = {
        "transaction_id": "",
        "customer_id": "C101",
        "amount": -50,
        "timestamp": "not-a-date",
        "latitude": 150.0,  # Invalid latitude
        "longitude": 77.0,
        "location_name": "Delhi",
        "merchant": "Demo Store",
        "transaction_type": "PURCHASE",
        "channel": "UPI",
    }
    status_inv, resp_inv = send_post("/api/transactions", payload_invalid)
    print(f"\n4. Test Invalid Payload -> HTTP {status_inv} (Expected 422 Unprocessable Entity)")

    # Test 4: Verify NO rows were inserted into DB
    with get_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS cnt FROM transactions;")
        count_after = cursor.fetchone()["cnt"]

    print(f"\n5. Database Immutability Check:")
    print(f"   Rows before: {count_before}")
    print(f"   Rows after:  {count_after}")
    print(f"   New transaction persisted into DB? {'NO (Correct)' if count_before == count_after else 'YES (Incorrect!)'}")

    print("\n=== STEP 3 VERIFICATION COMPLETE ===")


if __name__ == "__main__":
    main()
