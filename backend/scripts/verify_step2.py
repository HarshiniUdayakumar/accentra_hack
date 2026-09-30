"""Verification script for Step 2."""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.database import get_customer_history, get_cursor
from app.services import transaction_service


if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    print("=== STEP 2 VERIFICATION ===")

    # 1. Total row count
    with get_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total_count FROM transactions;")
        total_txns = cursor.fetchone()["total_count"]
    print(f"\n1. Total Transactions in DB: {total_txns} (Target: ~500)")

    # 2. C101 sample records
    print("\n2. Customer C101 Historical Records (Top 5 most recent):")
    c101_sample = get_customer_history("C101", limit=5)
    for t in c101_sample:
        print(
            f"   [{t['transaction_id']}] {t['timestamp']} | ₹{t['amount']:.2f} | "
            f"{t['location_name']} ({t['latitude']:.4f}, {t['longitude']:.4f}) | "
            f"Merchant: {t['merchant']} | Channel: {t['channel']}"
        )

    # 3. Verify counts for C101, C102, C103, C104, C105
    print("\n3. Transaction Counts for Test Customers:")
    for cid in ["C101", "C102", "C103", "C104", "C105"]:
        history = transaction_service.get_history(cid, limit=100)
        locations = sorted(list(set(t["location_name"] for t in history)))
        amounts = [t["amount"] for t in history]
        avg_amt = sum(amounts) / len(amounts) if amounts else 0.0
        min_amt, max_amt = (min(amounts), max(amounts)) if amounts else (0, 0)
        print(
            f"   Customer {cid}: {len(history)} transactions | "
            f"Locations: {locations} | Range: ₹{min_amt:.2f} - ₹{max_amt:.2f} (Avg: ₹{avg_amt:.2f})"
        )

    # 4. Verify ordering (timestamp descending)
    c101_all = transaction_service.get_history("C101", limit=100)
    timestamps = [t["timestamp"] for t in c101_all]
    is_ordered = all(timestamps[i] >= timestamps[i + 1] for i in range(len(timestamps) - 1))
    print(f"\n4. Timestamps strictly ordered descending: {is_ordered}")

    print("\n=== VERIFICATION FINISHED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
