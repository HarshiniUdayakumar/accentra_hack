"""Feature extraction pipeline for behavioral anomaly detection.

Extracts identical behavioral feature vectors during both offline model training
and real-time inference on incoming transactions with customer history.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from app.rules.base import parse_timestamp, to_dict

# Canonical list and ordering of ML input features
FEATURE_NAMES: List[str] = [
    "amount",
    "transactions_last_5m",
    "transactions_last_1h",
    "transactions_today",
    "historical_average_amount",
    "historical_maximum_amount",
    "historical_minimum_amount",
    "amount_deviation",
    "time_since_previous_transaction",
    "transaction_hour",
    "transaction_day_of_week",
]


class FeatureBuilder:
    """Builds numerical behavioral features from transactions and customer histories."""

    def __init__(self, feature_names: Optional[List[str]] = None):
        self.feature_names = list(feature_names) if feature_names else list(FEATURE_NAMES)

    def extract_features(
        self,
        transaction: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, float]:
        """Extract a single feature dictionary from a transaction and customer history.

        Args:
            transaction: Transaction dictionary or payload.
            history: Optional list of previous customer transactions.

        Returns:
            Dictionary containing all feature values keyed by feature name.
        """
        txn_dict = to_dict(transaction)
        amount = float(txn_dict.get("amount", 0.0))
        current_tx_id = txn_dict.get("transaction_id")

        try:
            current_time = parse_timestamp(txn_dict["timestamp"])
        except Exception:
            current_time = datetime.now()

        hour = float(current_time.hour)
        day_of_week = float(current_time.weekday())

        # Process historical transactions
        valid_history: List[tuple] = []
        if history:
            for h in history:
                h_dict = to_dict(h)
                if current_tx_id and h_dict.get("transaction_id") == current_tx_id:
                    continue

                ts_raw = h_dict.get("timestamp")
                if not ts_raw:
                    continue

                try:
                    h_time = parse_timestamp(ts_raw)
                except Exception:
                    continue

                if h_time <= current_time:
                    try:
                        amt = float(h_dict.get("amount", 0.0))
                    except (ValueError, TypeError):
                        amt = 0.0
                    valid_history.append((h_time, amt))

        # Handle history statistics
        if valid_history:
            amounts = [v[1] for v in valid_history]
            hist_avg = float(np.mean(amounts))
            hist_max = float(np.max(amounts))
            hist_min = float(np.min(amounts))
            amount_dev = float(amount - hist_avg)

            # Rolling window frequencies
            count_5m = 0.0
            count_1h = 0.0
            count_today = 0.0
            min_delta_sec = float("inf")
            current_date = current_time.date()

            for h_time, _ in valid_history:
                delta_sec = (current_time - h_time).total_seconds()
                if delta_sec >= 0:
                    if delta_sec < min_delta_sec:
                        min_delta_sec = delta_sec
                    if delta_sec <= 300:
                        count_5m += 1.0
                    if delta_sec <= 3600:
                        count_1h += 1.0
                    if h_time.date() == current_date or delta_sec <= 86400:
                        count_today += 1.0

            time_since_prev = min_delta_sec if min_delta_sec != float("inf") else 86400.0
        else:
            # Safe cold-start defaults for customers with empty/missing history
            hist_avg = amount
            hist_max = amount
            hist_min = amount
            amount_dev = 0.0
            count_5m = 0.0
            count_1h = 0.0
            count_today = 0.0
            time_since_prev = 86400.0  # 24 hours in seconds (neutral interval)

        feature_map: Dict[str, float] = {
            "amount": amount,
            "transactions_last_5m": float(count_5m),
            "transactions_last_1h": float(count_1h),
            "transactions_today": float(count_today),
            "historical_average_amount": float(hist_avg),
            "historical_maximum_amount": float(hist_max),
            "historical_minimum_amount": float(hist_min),
            "amount_deviation": float(amount_dev),
            "time_since_previous_transaction": float(time_since_prev),
            "transaction_hour": hour,
            "transaction_day_of_week": day_of_week,
        }

        return feature_map

    def build_feature_vector(
        self,
        transaction: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> np.ndarray:
        """Extract features and return a 2D numpy array in exact feature_names order.

        Args:
            transaction: Transaction dictionary or payload.
            history: Optional list of previous customer transactions.

        Returns:
            2D numpy array of shape (1, len(feature_names)).
        """
        feat_dict = self.extract_features(transaction=transaction, history=history)
        vector = [feat_dict[k] for k in self.feature_names]
        return np.array([vector], dtype=np.float64)

    def extract_features_from_paysim(
        self, df: pd.DataFrame, n_customers: int = 2000
    ) -> pd.DataFrame:
        """Transform PaySim records into the standardized behavioral feature matrix.

        Partitions transactions into customer timelines to establish realistic
        prior spending histories and intervals, ensuring parity with inference.

        Args:
            df: PaySim DataFrame with columns (step, amount, nameOrig, etc.).
            n_customers: Number of customer streams to partition originators across.

        Returns:
            DataFrame containing exactly self.feature_names in defined column order.
        """
        temp_df = df.copy()

        # Map originators to customer groups to create longitudinal spending profiles
        temp_df["cust_group"] = temp_df["nameOrig"].apply(lambda x: hash(x) % n_customers)
        temp_df = temp_df.sort_values(by=["cust_group", "step"]).reset_index(drop=True)

        grouped = temp_df.groupby("cust_group")

        # Expanding historical amounts prior to current row
        hist_avg = (
            grouped["amount"]
            .transform(lambda s: s.shift(1).expanding().mean())
            .fillna(temp_df["amount"])
        )
        hist_max = (
            grouped["amount"]
            .transform(lambda s: s.shift(1).expanding().max())
            .fillna(temp_df["amount"])
        )
        hist_min = (
            grouped["amount"]
            .transform(lambda s: s.shift(1).expanding().min())
            .fillna(temp_df["amount"])
        )
        amount_dev = temp_df["amount"] - hist_avg

        # Elapsed time intervals based on PaySim steps (1 step = 1 hour)
        step_diff = temp_df["step"] - grouped["step"].shift(1)
        time_since_prev = (step_diff * 3600.0).fillna(86400.0)

        # Velocity features
        tx_last_1h = (step_diff <= 1).astype(float).fillna(0.0)
        tx_last_5m = (step_diff == 0).astype(float).fillna(0.0)
        tx_today = (step_diff <= 24).astype(float).fillna(0.0)

        tx_hour = ((temp_df["step"] - 1) % 24).astype(float)
        tx_day_of_week = (((temp_df["step"] - 1) // 24) % 7).astype(float)

        feature_matrix = pd.DataFrame(
            {
                "amount": temp_df["amount"].astype(float),
                "transactions_last_5m": tx_last_5m,
                "transactions_last_1h": tx_last_1h,
                "transactions_today": tx_today,
                "historical_average_amount": hist_avg.astype(float),
                "historical_maximum_amount": hist_max.astype(float),
                "historical_minimum_amount": hist_min.astype(float),
                "amount_deviation": amount_dev.astype(float),
                "time_since_previous_transaction": time_since_prev,
                "transaction_hour": tx_hour,
                "transaction_day_of_week": tx_day_of_week,
            },
            columns=self.feature_names,
        )

        return feature_matrix


# Global default instance
default_feature_builder = FeatureBuilder()
