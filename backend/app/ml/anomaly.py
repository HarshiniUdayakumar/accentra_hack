"""Behavioral anomaly detection using trained Isolation Forest model.

Provides a clean inference interface around the saved Isolation Forest artifact.
Evaluates transactions to produce an explainable numerical anomaly score and
categorical anomaly status (NORMAL or ANOMALOUS) without asserting definitive fraud.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd

from app.ml.feature_builder import FEATURE_NAMES, FeatureBuilder


class IsolationForestAnomalyDetector:
    """Inference engine for behavioral transaction anomaly detection."""

    def __init__(self, model_path: Optional[str] = None):
        """Initialize detector with optional model artifact path.

        Args:
            model_path: Filepath to saved joblib artifact. If None, resolves to
                        ml_models/isolation_forest.joblib relative to project root.
        """
        self.model_path = model_path or self._resolve_default_model_path()
        self.model: Optional[Any] = None
        self.feature_names: List[str] = list(FEATURE_NAMES)
        self.calibration: Dict[str, float] = {"min_score": 0.0, "max_score": 1.0}
        self.is_loaded: bool = False
        self.feature_builder = FeatureBuilder(self.feature_names)

    @staticmethod
    def _resolve_default_model_path() -> str:
        """Find the default model artifact location in ml_models/."""
        current_dir = Path(__file__).resolve().parent  # backend/app/ml
        backend_dir = current_dir.parent.parent        # backend/
        project_root = backend_dir.parent             # hybrid-fraud-detection/

        candidate_paths = [
            project_root / "ml_models" / "isolation_forest.joblib",
            backend_dir / "ml_models" / "isolation_forest.joblib",
            Path("ml_models") / "isolation_forest.joblib",
        ]
        for p in candidate_paths:
            if p.exists():
                return str(p)
        return str(candidate_paths[0])

    def load_model(self, model_path: Optional[str] = None) -> None:
        """Load the trained Isolation Forest artifact from disk.

        Args:
            model_path: Optional override path to the joblib artifact.
        """
        target_path = model_path or self.model_path
        if not os.path.exists(target_path):
            raise FileNotFoundError(
                f"Isolation Forest model artifact not found at: '{target_path}'. "
                f"Please run backend/app/ml/train_model.py first."
            )

        artifact = joblib.load(target_path)
        if isinstance(artifact, dict) and "model" in artifact:
            self.model = artifact["model"]
            self.feature_names = artifact.get("feature_names", list(FEATURE_NAMES))
            self.calibration = artifact.get(
                "score_calibration", {"min_score": -0.5, "max_score": 0.5}
            )
        else:
            # Fallback for plain estimator instance
            self.model = artifact
            self.feature_names = list(FEATURE_NAMES)

        self.feature_builder = FeatureBuilder(self.feature_names)
        self.is_loaded = True

    def _prepare_vector(
        self, features: Union[Dict[str, Any], np.ndarray, pd.DataFrame, List[float]]
    ) -> pd.DataFrame:
        """Format input features into DataFrame matching exact trained feature names and order."""
        if isinstance(features, dict):
            row = {k: float(features.get(k, 0.0)) for k in self.feature_names}
            return pd.DataFrame([row], columns=self.feature_names)

        if isinstance(features, pd.DataFrame):
            return features.reindex(columns=self.feature_names, fill_value=0.0)

        if isinstance(features, np.ndarray):
            arr = features.reshape(1, -1) if features.ndim == 1 else features
            return pd.DataFrame(arr, columns=self.feature_names)

        if isinstance(features, list):
            arr = np.array(features, dtype=np.float64)
            arr = arr.reshape(1, -1) if arr.ndim == 1 else arr
            return pd.DataFrame(arr, columns=self.feature_names)

        raise TypeError(f"Unsupported features type: {type(features)}")

    def predict(
        self, features: Union[Dict[str, Any], np.ndarray, pd.DataFrame, List[float]]
    ) -> Dict[str, Any]:
        """Perform behavioral anomaly inference on a feature vector.

        Args:
            features: Dictionary, numpy array, or DataFrame containing feature values.

        Returns:
            Dictionary containing:
            - anomaly_score: Normalized numerical score in [0.0, 1.0] (higher = more anomalous)
            - anomaly_status: Categorical designation ('ANOMALOUS' or 'NORMAL')
            - is_anomaly: Boolean flag indicating anomaly status
            - raw_score: Uncalibrated raw decision function output
        """
        if not self.is_loaded:
            self.load_model()

        X = self._prepare_vector(features)

        # Scikit-learn decision_function returns negative values for anomalies, positive for normal
        raw_decision = float(self.model.decision_function(X)[0])
        raw_anomaly = -raw_decision  # Higher indicates more anomalous

        # Normalize score to [0.0, 1.0] range using calibration bounds
        min_s = self.calibration.get("min_score", -0.3)
        max_s = self.calibration.get("max_score", 0.3)
        span = max_s - min_s if max_s > min_s else 1.0

        normalized_score = (raw_anomaly - min_s) / span
        normalized_score = float(np.clip(normalized_score, 0.0, 1.0))

        # Model prediction: -1 = outlier / anomaly, 1 = inlier / normal
        prediction = int(self.model.predict(X)[0])
        is_anomaly = bool(prediction == -1)
        anomaly_status = "ANOMALOUS" if is_anomaly else "NORMAL"

        return {
            "anomaly_score": round(normalized_score, 4),
            "anomaly_status": anomaly_status,
            "is_anomaly": is_anomaly,
            "raw_score": round(raw_anomaly, 4),
        }

    def predict_anomaly(
        self, features: Union[Dict[str, Any], np.ndarray, pd.DataFrame, List[float]]
    ) -> Dict[str, Any]:
        """Alias for predict() to maintain backward compatibility."""
        return self.predict(features)

    def score_transaction(
        self,
        transaction: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """End-to-end pipeline: extract features from transaction + history and predict.

        Args:
            transaction: Transaction dictionary or model payload.
            history: Optional list of previous customer transactions.

        Returns:
            Anomaly inference result dictionary.
        """
        features = self.feature_builder.extract_features(
            transaction=transaction, history=history
        )
        return self.predict(features)


# Global singleton instance
anomaly_detector = IsolationForestAnomalyDetector()
