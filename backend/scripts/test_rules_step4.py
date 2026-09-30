"""Test script for Step 4: Verification of the Three Fraud Detection Rules.

Tests the independent operation and explainability of:
1. VelocityRule
2. AmountRule
3. LocationRule

Through the modular RuleEngine and TransactionService architecture:
Database -> Service -> Rule Engine -> Rules

Scenarios tested:
  TEST 1 - NORMAL: Customer C101 with normal frequency, amount, and location.
  TEST 2 - HIGH AMOUNT: Customer C101 with an unusual amount (Rs.90,000).
  TEST 3 - HIGH VELOCITY: Multiple transactions in the 5-minute velocity window.
  TEST 4 - IMPOSSIBLE LOCATION: Implausible speed (Chennai -> Delhi in 2.5 minutes).
  TEST 5 - LEGITIMATE MULTI-LOCATION: Rapid movement for customer C102 returning MITIGATED.
"""
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

# Ensure safe console output encoding on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.rules.base import RuleResult, RuleStatus
from app.rules.engine import RuleEngine
from app.rules.velocity import VelocityRule
from app.rules.amount import AmountRule
from app.rules.location import LocationRule
from app.services.transaction_service import transaction_service


def print_rule_results(results: List[RuleResult]) -> None:
    """Print RuleResult objects adhering strictly to the required format:
    - Rule name
    - Status
    - Risk points
    - Reason
    - Evidence
    - Mitigation
    """
    for res in results:
        print(f"  --------------------------------------------------")
        print(f"  Rule name   : {res.rule_name}")
        print(f"  Status      : {res.status.value}")
        print(f"  Risk points : {res.risk_points}")
        print(f"  Reason      : {res.reason}")
        print(f"  Evidence    : {json.dumps(res.evidence, indent=4, default=str)}")
        print(f"  Mitigation  : {res.mitigation}")


def run_test_1() -> bool:
    print("\n" + "=" * 70)
    print("TEST 1 - NORMAL SCENARIO")
    print("=" * 70)
    print("Context: Customer C101 with normal amount (Rs.850), normal location (Chennai),")
    print("and normal spacing (>4 hours since last transaction).")

    # Ingestion via Service layer: Database -> Service -> Rule Engine -> Rules
    new_txn = {
        "transaction_id": "TX_TEST_001_NORM",
        "customer_id": "C101",
        "amount": 850.0,
        "timestamp": "2026-09-30T14:30:00",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "location_name": "Chennai",
        "merchant": "Swiggy Chennai",
        "transaction_type": "PURCHASE",
        "channel": "UPI",
    }

    # Fetch history via service layer and evaluate rules
    results = transaction_service.evaluate_rules(transaction=new_txn)
    print_rule_results(results)

    statuses = {r.rule_name: r.status for r in results}
    all_normal = all(s == RuleStatus.NORMAL for s in statuses.values())
    print(f"\n>> TEST 1 RESULT: {'PASSED (All rules NORMAL)' if all_normal else 'FAILED'}")
    return all_normal


def run_test_2() -> bool:
    print("\n" + "=" * 70)
    print("TEST 2 - HIGH AMOUNT SCENARIO")
    print("=" * 70)
    print("Context: Customer C101 (historical avg: ~Rs.1,150, max: ~Rs.2,595) with amount = Rs.90,000.")
    print("Expected: AmountRule -> TRIGGERED, VelocityRule -> NORMAL, LocationRule -> NORMAL.")

    new_txn = {
        "transaction_id": "TX_TEST_002_AMT",
        "customer_id": "C101",
        "amount": 90000.0,
        "timestamp": "2026-09-30T14:30:00",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "location_name": "Chennai",
        "merchant": "Luxury Watch Boutique",
        "transaction_type": "PURCHASE",
        "channel": "CREDIT_CARD",
    }

    results = transaction_service.evaluate_rules(transaction=new_txn)
    print_rule_results(results)

    status_map = {r.rule_name: r.status for r in results}
    passed = (
        status_map.get("AmountRule") == RuleStatus.TRIGGERED
        and status_map.get("VelocityRule") == RuleStatus.NORMAL
        and status_map.get("LocationRule") == RuleStatus.NORMAL
    )
    print(f"\n>> TEST 2 RESULT: {'PASSED (AmountRule TRIGGERED as expected)' if passed else 'FAILED'}")
    return passed


def run_test_3() -> bool:
    print("\n" + "=" * 70)
    print("TEST 3 - HIGH VELOCITY SCENARIO")
    print("=" * 70)
    print("Context: 4 transactions occur within 5 minutes of new transaction for C101.")
    print("Configured threshold: 3 transactions within 5 minutes.")
    print("Expected: VelocityRule -> TRIGGERED.")

    base_time = datetime(2026, 9, 30, 10, 20, 0)
    new_txn = {
        "transaction_id": "TX_TEST_003_VEL",
        "customer_id": "C101",
        "amount": 450.0,
        "timestamp": base_time.isoformat(),
        "latitude": 13.0827,
        "longitude": 80.2707,
        "location_name": "Chennai",
        "merchant": "Quick Commerce Grocery",
        "transaction_type": "PURCHASE",
        "channel": "UPI",
    }

    # Fetch C101's base history from MySQL (latest is at 10:17:35, which is 2m 25s prior)
    # Augment with 3 additional rapid transactions so total within 5 min is exactly 4 (threshold: 3)
    base_history = transaction_service.get_history("C101")
    rapid_transactions = [
        {
            "transaction_id": "TX_RAPID_003",
            "customer_id": "C101",
            "amount": 350.0,
            "timestamp": (base_time - timedelta(seconds=30)).isoformat(),
            "latitude": 13.0827,
            "longitude": 80.2707,
            "location_name": "Chennai",
            "merchant": "Swiggy Chennai",
            "transaction_type": "PURCHASE",
            "channel": "UPI",
        },
        {
            "transaction_id": "TX_RAPID_002",
            "customer_id": "C101",
            "amount": 280.0,
            "timestamp": (base_time - timedelta(seconds=75)).isoformat(),
            "latitude": 13.0827,
            "longitude": 80.2707,
            "location_name": "Chennai",
            "merchant": "Uber Chennai",
            "transaction_type": "PAYMENT",
            "channel": "UPI",
        },
        {
            "transaction_id": "TX_RAPID_001",
            "customer_id": "C101",
            "amount": 420.0,
            "timestamp": (base_time - timedelta(seconds=120)).isoformat(),
            "latitude": 13.0827,
            "longitude": 80.2707,
            "location_name": "Chennai",
            "merchant": "Apollo Pharmacy Adyar",
            "transaction_type": "PURCHASE",
            "channel": "UPI",
        },
    ]
    augmented_history = rapid_transactions + base_history

    results = transaction_service.evaluate_rules(
        transaction=new_txn, history=augmented_history
    )
    print_rule_results(results)

    status_map = {r.rule_name: r.status for r in results}
    passed = status_map.get("VelocityRule") == RuleStatus.TRIGGERED
    print(f"\n>> TEST 3 RESULT: {'PASSED (VelocityRule TRIGGERED with >3 txns in 5m)' if passed else 'FAILED'}")
    return passed


def run_test_4() -> bool:
    print("\n" + "=" * 70)
    print("TEST 4 - IMPOSSIBLE LOCATION SCENARIO")
    print("=" * 70)
    print("Context: C101 previous transaction in Chennai at 10:17:35.")
    print("New transaction in Delhi at 10:20:00 (elapsed: ~2.4 mins, distance: ~1,757 km).")
    print("Expected: LocationRule -> TRIGGERED with implausible travel speed.")

    # C101 in DB has latest record at 2026-09-30 10:17:35 in Chennai
    new_txn = {
        "transaction_id": "TX_TEST_004_LOC",
        "customer_id": "C101",
        "amount": 1200.0,
        "timestamp": "2026-09-30T10:20:00",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "location_name": "Delhi",
        "merchant": "Modern Bazaar CP",
        "transaction_type": "PURCHASE",
        "channel": "POS",
    }

    results = transaction_service.evaluate_rules(transaction=new_txn)
    print_rule_results(results)

    status_map = {r.rule_name: r.status for r in results}
    passed = (
        status_map.get("LocationRule") == RuleStatus.TRIGGERED
        and status_map.get("AmountRule") == RuleStatus.NORMAL
    )
    print(f"\n>> TEST 4 RESULT: {'PASSED (LocationRule TRIGGERED for impossible travel)' if passed else 'FAILED'}")
    return passed


def run_test_5() -> bool:
    print("\n" + "=" * 70)
    print("TEST 5 - LEGITIMATE MULTI-LOCATION SCENARIO")
    print("=" * 70)
    print("Context: Customer C102 (registered in LEGITIMATE_MULTI_LOCATION_CUSTOMERS).")
    print("Previous location: Chennai at 09:31:17.")
    print("New location: Bangalore at 09:35:00 (elapsed: ~3.7 mins, distance: ~290 km).")
    print("Expected: LocationRule -> MITIGATED (not blindly triggered).")

    new_txn = {
        "transaction_id": "TX_TEST_005_MITIGATED",
        "customer_id": "C102",
        "amount": 2500.0,
        "timestamp": "2026-09-30T09:35:00",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "location_name": "Bangalore",
        "merchant": "Indiranagar Cafe",
        "transaction_type": "PURCHASE",
        "channel": "CREDIT_CARD",
    }

    results = transaction_service.evaluate_rules(transaction=new_txn)
    print_rule_results(results)

    loc_result = next((r for r in results if r.rule_name == "LocationRule"), None)
    passed = (
        loc_result is not None
        and loc_result.status == RuleStatus.MITIGATED
        and loc_result.mitigation is not None
    )
    print(f"\n>> TEST 5 RESULT: {'PASSED (LocationRule returned MITIGATED with explanation)' if passed else 'FAILED'}")
    return passed


def main():
    print("=" * 70)
    print("STEP 4: FRAUD DETECTION RULES VERIFICATION SUITE")
    print("=" * 70)

    # 1. Architecture modularity check
    engine = RuleEngine()
    print(f"Registered rules in RuleEngine: {engine.registered_rules}")
    assert set(engine.registered_rules) == {"VelocityRule", "AmountRule", "LocationRule"}

    # 2. Run the 5 required test scenarios
    results = [
        ("TEST 1 - NORMAL", run_test_1()),
        ("TEST 2 - HIGH AMOUNT", run_test_2()),
        ("TEST 3 - HIGH VELOCITY", run_test_3()),
        ("TEST 4 - IMPOSSIBLE LOCATION", run_test_4()),
        ("TEST 5 - LEGITIMATE MULTI-LOCATION", run_test_5()),
    ]

    print("\n" + "=" * 70)
    print("SUMMARY OF TEST RESULTS")
    print("=" * 70)
    all_passed = True
    for test_name, status in results:
        status_str = "PASSED" if status else "FAILED"
        print(f"  {test_name.ljust(40)}: {status_str}")
        if not status:
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("ALL STEP 4 RULES TESTS PASSED SUCCESSFULLY!")
    else:
        print("SOME TESTS FAILED - PLEASE REVIEW.")
    print("=" * 70)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
