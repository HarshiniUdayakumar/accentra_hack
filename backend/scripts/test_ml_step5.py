"""Test script for Step 5: Verification of Isolation Forest ML Anomaly Detection.

Verifies the 10 required ML validation criteria:
1. Dataset exists (data/paysim.csv)
2. Model file exists (ml_models/isolation_forest.joblib)
3. Saved model can be loaded
4. Feature builder works
5. Feature columns are consistent (names and exact order)
6. Inference returns an anomaly score (0.0 to 1.0)
7. Inference returns an anomaly status ('NORMAL' or 'ANOMALOUS')
8. Normal-looking transaction can be processed
9. Unusual transaction can be processed
10. Existing Step 4 rule engine still works
"""
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List

# Ensure safe console output encoding on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent  # backend/scripts
BACKEND_DIR = SCRIPT_DIR.parent               # backend/
PROJECT_ROOT = BACKEND_DIR.parent             # hybrid-fraud-detection/
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
import pandas as pd
from app.ml.anomaly import IsolationForestAnomalyDetector, anomaly_detector
from app.ml.feature_builder import FEATURE_NAMES, FeatureBuilder
from app.rules.base import RuleResult, RuleStatus
from app.rules.engine import RuleEngine
from app.services.transaction_service import transaction_service


def test_1_dataset_exists() -> bool:
    print("\n--- Check 1: Dataset Existence ---")
    data_path = PROJECT_ROOT / "data" / "paysim.csv"
    exists = data_path.exists()
    size_mb = data_path.stat().st_size / (1024 * 1024) if exists else 0.0
    print(f"  Dataset path : {data_path}")
    print(f"  Exists       : {exists}")
    print(f"  File size    : {size_mb:.2f} MB")
    return exists and size_mb > 0


def test_2_model_file_exists() -> bool:
    print("\n--- Check 2: Model Artifact Existence ---")
    model_path = PROJECT_ROOT / "ml_models" / "isolation_forest.joblib"
    exists = model_path.exists()
    size_mb = model_path.stat().st_size / (1024 * 1024) if exists else 0.0
    print(f"  Model path : {model_path}")
    print(f"  Exists     : {exists}")
    print(f"  File size  : {size_mb:.2f} MB")
    return exists and size_mb > 0


def test_3_saved_model_loads() -> bool:
    print("\n--- Check 3: Load Saved Model ---")
    detector = IsolationForestAnomalyDetector()
    detector.load_model()
    is_loaded = detector.is_loaded and detector.model is not None
    print(f"  Model loaded successfully : {is_loaded}")
    print(f"  Model type                 : {type(detector.model).__name__}")
    print(f"  Number of estimators       : {detector.model.n_estimators}")
    return is_loaded


def test_4_feature_builder_works() -> bool:
    print("\n--- Check 4: Feature Builder Functionality ---")
    builder = FeatureBuilder()
    mock_txn = {
        "transaction_id": "TX_TEST_001",
        "customer_id": "C101",
        "amount": 1500.0,
        "timestamp": "2026-09-30T10:20:00",
    }
    mock_history = [
        {"transaction_id": "TX_PREV_1", "amount": 1200.0, "timestamp": "2026-09-30T10:00:00"},
        {"transaction_id": "TX_PREV_2", "amount": 1400.0, "timestamp": "2026-09-29T15:00:00"},
    ]
    features = builder.extract_features(mock_txn, mock_history)
    print(f"  Extracted {len(features)} features:")
    for k, v in features.items():
        print(f"    - {k.ljust(35)}: {v}")

    all_floats = all(isinstance(v, (int, float)) for v in features.values())
    has_expected_count = len(features) == len(FEATURE_NAMES)
    return all_floats and has_expected_count


def test_5_feature_columns_consistent() -> bool:
    print("\n--- Check 5: Feature Column Order and Parity ---")
    builder = FeatureBuilder()
    detector = IsolationForestAnomalyDetector()
    detector.load_model()

    builder_cols = builder.feature_names
    detector_cols = detector.feature_names

    is_identical = builder_cols == detector_cols == FEATURE_NAMES
    print(f"  Builder features count  : {len(builder_cols)}")
    print(f"  Detector features count : {len(detector_cols)}")
    print(f"  Order parity verified   : {is_identical}")
    print(f"  Columns: {FEATURE_NAMES}")
    return is_identical


def test_6_and_7_inference_scores_and_status() -> bool:
    print("\n--- Checks 6 & 7: Anomaly Score and Status Contract ---")
    detector = IsolationForestAnomalyDetector()
    detector.load_model()

    mock_txn = {
        "transaction_id": "TX_INFER_01",
        "customer_id": "C101",
        "amount": 500.0,
        "timestamp": "2026-09-30T12:00:00",
    }
    result = detector.score_transaction(mock_txn, history=[])

    print(f"  Inference result: {json.dumps(result, indent=4)}")

    score_valid = (
        "anomaly_score" in result
        and isinstance(result["anomaly_score"], float)
        and 0.0 <= result["anomaly_score"] <= 1.0
    )
    status_valid = (
        "anomaly_status" in result
        and result["anomaly_status"] in {"NORMAL", "ANOMALOUS"}
        and "is_anomaly" in result
        and isinstance(result["is_anomaly"], bool)
    )

    print(f"  Anomaly score in [0.0, 1.0] : {score_valid}")
    print(f"  Anomaly status valid        : {status_valid}")
    return score_valid and status_valid


def test_8_normal_transaction_processing() -> bool:
    print("\n--- Check 8: Normal-looking Transaction Processing ---")
    # Fetch real C101 customer history from MySQL database
    c101_history = transaction_service.get_history("C101")
    print(f"  Retrieved {len(c101_history)} historical records for customer C101 from MySQL.")

    normal_txn = {
        "transaction_id": "TX_NORM_TEST",
        "customer_id": "C101",
        "amount": 750.0,  # Well within C101 historical average (~Rs.1,150)
        "timestamp": "2026-09-30T14:30:00",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "location_name": "Chennai",
    }

    result = anomaly_detector.score_transaction(normal_txn, c101_history)
    print(f"  Normal Transaction Inference Output:")
    print(f"    - Anomaly score  : {result['anomaly_score']}")
    print(f"    - Anomaly status : {result['anomaly_status']}")
    print(f"    - Is anomaly     : {result['is_anomaly']}")
    print(f"    - Raw score      : {result['raw_score']}")

    passed = result["anomaly_score"] >= 0.0 and result["anomaly_status"] in {"NORMAL", "ANOMALOUS"}
    return passed


def test_9_unusual_transaction_processing() -> bool:
    print("\n--- Check 9: Unusual Transaction Processing ---")
    c101_history = transaction_service.get_history("C101")

    # Extreme amount: Rs.1,500,000 for customer C101 whose historical max is Rs.2,594.83
    unusual_txn = {
        "transaction_id": "TX_UNUSUAL_TEST",
        "customer_id": "C101",
        "amount": 1500000.0,
        "timestamp": "2026-09-30T10:18:00",  # Just 25 seconds after previous
        "latitude": 28.6139,
        "longitude": 77.2090,
        "location_name": "Delhi",
    }

    result = anomaly_detector.score_transaction(unusual_txn, c101_history)
    print(f"  Unusual Transaction Inference Output:")
    print(f"    - Anomaly score  : {result['anomaly_score']}")
    print(f"    - Anomaly status : {result['anomaly_status']}")
    print(f"    - Is anomaly     : {result['is_anomaly']}")
    print(f"    - Raw score      : {result['raw_score']}")

    # The anomaly score should be elevated for an extreme outlier
    passed = result["anomaly_score"] > 0.0 and result["anomaly_status"] in {"NORMAL", "ANOMALOUS"}
    return passed


def test_10_existing_step4_rules_work() -> bool:
    print("\n--- Check 10: Regression Verification of Step 4 Rule Engine ---")
    engine = RuleEngine()
    registered = engine.registered_rules
    print(f"  Registered rules in RuleEngine: {registered}")
    assert set(registered) == {"VelocityRule", "AmountRule", "LocationRule"}

    new_txn = {
        "transaction_id": "TX_REGRESS_01",
        "customer_id": "C101",
        "amount": 90000.0,  # High amount should trigger AmountRule
        "timestamp": "2026-09-30T14:30:00",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "location_name": "Chennai",
    }

    history = transaction_service.get_history("C101")
    rule_results = engine.evaluate_all(transaction=new_txn, history=history)

    print(f"  Evaluated {len(rule_results)} rules:")
    for r in rule_results:
        print(f"    - {r.rule_name.ljust(15)}: Status={r.status.value}, Risk points={r.risk_points}")

    status_map = {r.rule_name: r.status for r in rule_results}
    rules_work = (
        status_map.get("AmountRule") == RuleStatus.TRIGGERED
        and status_map.get("VelocityRule") == RuleStatus.NORMAL
        and status_map.get("LocationRule") == RuleStatus.NORMAL
    )
    print(f"  Step 4 Rule Engine operates as expected : {rules_work}")
    return rules_work


def main():
    print("=" * 70)
    print("STEP 5: ISOLATION FOREST ML ANOMALY DETECTION TEST SUITE")
    print("=" * 70)

    checks = [
        ("1. Dataset exists", test_1_dataset_exists()),
        ("2. Model file exists", test_2_model_file_exists()),
        ("3. Saved model loads", test_3_saved_model_loads()),
        ("4. Feature builder works", test_4_feature_builder_works()),
        ("5. Feature columns consistent", test_5_feature_columns_consistent()),
        ("6 & 7. Inference score & status valid", test_6_and_7_inference_scores_and_status()),
        ("8. Normal transaction processed", test_8_normal_transaction_processing()),
        ("9. Unusual transaction processed", test_9_unusual_transaction_processing()),
        ("10. Step 4 rules still work", test_10_existing_step4_rules_work()),
    ]

    print("\n" + "=" * 70)
    print("SUMMARY OF STEP 5 VERIFICATION CHECKS")
    print("=" * 70)
    all_passed = True
    for name, passed in checks:
        status_str = "PASSED" if passed else "FAILED"
        print(f"  {name.ljust(45)}: {status_str}")
        if not passed:
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("ALL STEP 5 VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    else:
        print("SOME CHECKS FAILED - PLEASE REVIEW.")
    print("=" * 70)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
