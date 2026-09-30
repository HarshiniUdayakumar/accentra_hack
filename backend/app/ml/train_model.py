"""Isolation Forest training and evaluation script on PaySim dataset.

Trains an unsupervised IsolationForest model using behavioral transaction features.
PaySim's 'isFraud' label is NEVER used during feature building or model training;
it is strictly utilized post-training for benchmark validation and distribution analysis.
"""
from datetime import datetime
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, roc_auc_score

# Ensure backend root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent  # backend/app/ml
BACKEND_DIR = SCRIPT_DIR.parent.parent        # backend/
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ml.feature_builder import FEATURE_NAMES, FeatureBuilder


def get_data_path() -> Path:
    """Resolve absolute path to data/paysim.csv."""
    project_root = BACKEND_DIR.parent
    path = project_root / "data" / "paysim.csv"
    if not path.exists():
        raise FileNotFoundError(f"Required dataset not found at: {path}")
    return path


def get_model_path() -> Path:
    """Resolve target path for ml_models/isolation_forest.joblib."""
    project_root = BACKEND_DIR.parent
    model_dir = project_root / "ml_models"
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir / "isolation_forest.joblib"


def load_and_prepare_dataset(
    data_path: Path, n_rows: int = 100000, eval_split: float = 0.25
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Load PaySim sample and transform into behavioral feature matrices.

    Args:
        data_path: Path to paysim.csv.
        n_rows: Number of records to sample for training and evaluation.
        eval_split: Fraction reserved for post-training validation.

    Returns:
        Tuple of (X_train, X_eval, y_eval).
    """
    print(f"Loading {n_rows:,} records from: {data_path.name}...")
    t0 = time.time()
    df = pd.read_csv(data_path, nrows=n_rows)
    print(f"Loaded {len(df):,} rows in {time.time() - t0:.2f}s.")
    print(f"Total known fraud cases in sample: {int(df['isFraud'].sum()):,}")

    feature_builder = FeatureBuilder(FEATURE_NAMES)
    print("Extracting behavioral features using FeatureBuilder...")
    t1 = time.time()
    features = feature_builder.extract_features_from_paysim(df)
    print(f"Extracted {features.shape[1]} features for {len(features):,} rows in {time.time() - t1:.2f}s.")

    from sklearn.model_selection import train_test_split

    X_train, X_eval, y_train, y_eval = train_test_split(
        features,
        df["isFraud"],
        test_size=eval_split,
        random_state=42,
        stratify=df["isFraud"],
    )

    X_train = X_train.reset_index(drop=True)
    X_eval = X_eval.reset_index(drop=True)
    y_eval = y_eval.reset_index(drop=True)

    return X_train, X_eval, y_eval


def train_isolation_forest(
    X_train: pd.DataFrame,
    contamination: float = 0.03,
    random_state: int = 42,
    n_estimators: int = 100,
) -> IsolationForest:
    """Train unsupervised Isolation Forest on behavioral transaction features.

    Args:
        X_train: Feature DataFrame without labels.
        contamination: Estimated anomaly contamination factor.
        random_state: Fixed random seed for reproducibility.
        n_estimators: Number of isolation trees.

    Returns:
        Fitted IsolationForest model.
    """
    print("\nTraining Isolation Forest anomaly detector (unsupervised)...")
    print(f"  Configuration: n_estimators={n_estimators}, contamination={contamination}, random_state={random_state}")
    t0 = time.time()
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train)
    print(f"  Model trained successfully in {time.time() - t0:.2f}s.")
    return model


def evaluate_model(
    model: IsolationForest,
    X_eval: pd.DataFrame,
    y_eval: pd.Series,
    raw_train_scores: np.ndarray,
) -> Dict[str, Any]:
    """Evaluate Isolation Forest predictions against known PaySim labels.

    Args:
        model: Fitted Isolation Forest.
        X_eval: Evaluation feature set.
        y_eval: Known PaySim isFraud labels (evaluation only).
        raw_train_scores: Raw scores from training set to establish score calibration.

    Returns:
        Dictionary of evaluation metrics.
    """
    print("\n" + "=" * 70)
    print("EVALUATION ON PAYSIM BENCHMARK DATASET")
    print("=" * 70)
    print("Note: PaySim is a synthetic dataset. Results indicate comparative anomaly")
    print("separation capacity on synthetic patterns, not real-world fraud accuracy.")

    # Raw anomaly score: negative decision function (higher is more anomalous)
    raw_eval_scores = -model.decision_function(X_eval)

    # Score calibration bounds (robust percentiles from training distribution)
    min_s = float(np.percentile(raw_train_scores, 1))
    max_s = float(np.percentile(raw_train_scores, 99))
    span = max_s - min_s if max_s > min_s else 1.0

    norm_scores = (raw_eval_scores - min_s) / span
    norm_scores = np.clip(norm_scores, 0.0, 1.0)

    eval_df = pd.DataFrame(
        {
            "anomaly_score": norm_scores,
            "raw_score": raw_eval_scores,
            "isFraud": y_eval.values,
        }
    )

    normal_subset = eval_df[eval_df["isFraud"] == 0]["anomaly_score"]
    fraud_subset = eval_df[eval_df["isFraud"] == 1]["anomaly_score"]

    n_normal = len(normal_subset)
    n_fraud = len(fraud_subset)

    print(f"\nEvaluation Set Size: {len(eval_df):,} records")
    print(f"  - Known Normal Transactions : {n_normal:,} ({(n_normal/len(eval_df))*100:.2f}%)")
    print(f"  - Known Fraud Transactions  : {n_fraud:,} ({(n_fraud/len(eval_df))*100:.2f}%)")

    print("\nAnomaly Score Distribution (Normalized 0.0 - 1.0, Higher = More Anomalous):")
    print(f"  - Normal Transactions -> Mean: {normal_subset.mean():.4f}, Median: {normal_subset.median():.4f}, Std: {normal_subset.std():.4f}")
    print(f"  - Fraud Transactions  -> Mean: {fraud_subset.mean():.4f}, Median: {fraud_subset.median():.4f}, Std: {fraud_subset.std():.4f}")

    # Binary prediction evaluation based on model's internal threshold
    preds = model.predict(X_eval)
    predicted_anomalies = (preds == -1).astype(int)

    auc_score = 0.0
    if n_fraud > 0 and n_normal > 0:
        auc_score = float(roc_auc_score(y_eval, raw_eval_scores))
        print(f"\nROC-AUC Score on PaySim Evaluation Split: {auc_score:.4f}")

    print("\nClassification Summary (Anomalous vs Normal):")
    print(f"  Total Anomalies Flagged by Model : {predicted_anomalies.sum():,} ({(predicted_anomalies.sum()/len(eval_df))*100:.2f}%)")
    if n_fraud > 0:
        fraud_flagged = int(((predicted_anomalies == 1) & (y_eval.values == 1)).sum())
        recall = fraud_flagged / n_fraud
        print(f"  Fraud Anomalies Detected (Recall) : {fraud_flagged} of {n_fraud} ({recall*100:.1f}%)")

    return {
        "n_eval": len(eval_df),
        "n_normal": n_normal,
        "n_fraud": n_fraud,
        "normal_mean_score": round(float(normal_subset.mean()), 4),
        "fraud_mean_score": round(float(fraud_subset.mean()), 4),
        "roc_auc": round(auc_score, 4),
        "min_score": min_s,
        "max_score": max_s,
    }


def main():
    data_path = get_data_path()
    model_path = get_model_path()

    print("=" * 70)
    print("STEP 5: ISOLATION FOREST ML ANOMALY DETECTION TRAINING")
    print("=" * 70)

    # 1. Load data and extract behavioral features
    X_train, X_eval, y_eval = load_and_prepare_dataset(data_path=data_path, n_rows=100000)

    # 2. Train Isolation Forest
    contamination = 0.03
    random_state = 42
    model = train_isolation_forest(
        X_train=X_train, contamination=contamination, random_state=random_state
    )

    # 3. Score training set for calibration
    raw_train_scores = -model.decision_function(X_train)

    # 4. Evaluate against PaySim known fraud labels (post-training only)
    eval_metrics = evaluate_model(
        model=model,
        X_eval=X_eval,
        y_eval=y_eval,
        raw_train_scores=raw_train_scores,
    )

    # 5. Save model bundle
    artifact = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "contamination": contamination,
        "score_calibration": {
            "min_score": eval_metrics["min_score"],
            "max_score": eval_metrics["max_score"],
        },
        "training_metadata": {
            "n_training_samples": len(X_train),
            "n_eval_samples": len(X_eval),
            "feature_names": FEATURE_NAMES,
            "contamination": contamination,
            "random_state": random_state,
            "trained_at": datetime.now().isoformat(),
            "dataset": "PaySim (synthetic)",
            "eval_metrics": eval_metrics,
        },
    }

    print(f"\nSaving model artifact to: {model_path}...")
    joblib.dump(artifact, model_path)
    file_size_mb = os.path.getsize(model_path) / (1024 * 1024)
    print(f"Artifact saved successfully ({file_size_mb:.2f} MB).")
    print("=" * 70)
    print("TRAINING PROCESS COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
