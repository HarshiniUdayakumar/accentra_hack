"""Transaction velocity detection rule component.

Evaluates the frequency of transactions associated with a customer over multiple
time windows (5 minutes, 1 hour, and today). High frequency of transactions within
short windows generates an explainable risk signal without forming a final fraud verdict.
"""
from typing import Any, Dict, List, Optional
from app.rules.base import BaseRule, RuleResult, RuleStatus, parse_timestamp, to_dict


class VelocityRule(BaseRule):
    """Detects unusually high frequency of transactions within short rolling windows."""

    def __init__(
        self,
        name: str = "VelocityRule",
        weight: float = 1.0,
        threshold_5m: int = 3,
        threshold_1h: int = 10,
        threshold_today: int = 25,
        risk_points_5m: float = 75.0,
        risk_points_1h: float = 50.0,
        risk_points_today: float = 30.0,
    ):
        """Initialize VelocityRule with configurable detection thresholds.

        Args:
            name: Rule identifier.
            weight: Relative rule weight.
            threshold_5m: Max acceptable transactions in last 5 minutes (default: 3).
            threshold_1h: Max acceptable transactions in last 1 hour (default: 10).
            threshold_today: Max acceptable transactions in current day / 24 hours (default: 25).
            risk_points_5m: Risk points assigned when 5-minute velocity threshold is exceeded.
            risk_points_1h: Risk points assigned when 1-hour velocity threshold is exceeded.
            risk_points_today: Risk points assigned when 24-hour velocity threshold is exceeded.
        """
        super().__init__(name=name, weight=weight)
        self.threshold_5m = threshold_5m
        self.threshold_1h = threshold_1h
        self.threshold_today = threshold_today
        self.risk_points_5m = risk_points_5m
        self.risk_points_1h = risk_points_1h
        self.risk_points_today = risk_points_today

    def evaluate(
        self,
        transaction: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RuleResult:
        """Evaluate transaction velocity against historical records.

        Args:
            transaction: Current transaction payload or dict.
            history: Optional list of previous customer transactions.
            context: Optional contextual parameters (e.g. whitelist flags).

        Returns:
            RuleResult with velocity counts, thresholds, status, and reason.
        """
        txn_dict = to_dict(transaction)
        customer_id = str(txn_dict.get("customer_id", "Unknown"))
        current_tx_id = txn_dict.get("transaction_id")

        try:
            current_time = parse_timestamp(txn_dict["timestamp"])
        except Exception as e:
            return RuleResult(
                rule_name=self.name,
                status=RuleStatus.NORMAL,
                risk_points=0.0,
                reason=f"Unable to evaluate velocity due to invalid timestamp: {e}",
                evidence={"error": str(e), "customer_id": customer_id},
                mitigation=None,
            )

        count_5m = 0
        count_1h = 0
        count_today = 0
        current_date = current_time.date()

        if history:
            for h in history:
                h_dict = to_dict(h)
                # Skip current transaction if it happens to be present in history
                if current_tx_id and h_dict.get("transaction_id") == current_tx_id:
                    continue

                raw_ts = h_dict.get("timestamp")
                if not raw_ts:
                    continue

                try:
                    h_time = parse_timestamp(raw_ts)
                except Exception:
                    continue

                delta_seconds = (current_time - h_time).total_seconds()
                # Consider transactions that occurred before or concurrently with the current transaction
                if delta_seconds >= 0:
                    if delta_seconds <= 300:  # 5 minutes
                        count_5m += 1
                    if delta_seconds <= 3600:  # 1 hour
                        count_1h += 1
                    if h_time.date() == current_date or delta_seconds <= 86400:
                        count_today += 1

        evidence: Dict[str, Any] = {
            "transactions_last_5_minutes": count_5m,
            "threshold": self.threshold_5m,
            "threshold_5_minutes": self.threshold_5m,
            "transactions_last_1_hour": count_1h,
            "threshold_1_hour": self.threshold_1h,
            "transactions_today": count_today,
            "threshold_today": self.threshold_today,
            "customer_id": customer_id,
            "current_timestamp": current_time.isoformat(),
        }

        # Check for whitelisted legitimate context
        is_mitigated = False
        mitigation_reason: Optional[str] = None
        if context:
            if context.get("authorized_bulk_operations") or context.get("is_automated_system"):
                is_mitigated = True
                mitigation_reason = (
                    f"Customer '{customer_id}' is authorized for high-frequency automated batch operations."
                )

        # Trigger logic based on hierarchy of windows
        if count_5m > self.threshold_5m:
            if is_mitigated:
                return RuleResult(
                    rule_name=self.name,
                    status=RuleStatus.MITIGATED,
                    risk_points=15.0,
                    reason=f"{count_5m} transactions occurred within the last 5 minutes (mitigated by authorized bulk status).",
                    evidence=evidence,
                    mitigation=mitigation_reason,
                )
            # Risk points scale slightly with excessive frequency capped at 95.0
            excess = count_5m - self.threshold_5m
            points = min(95.0, self.risk_points_5m + (excess * 5.0))
            return RuleResult(
                rule_name=self.name,
                status=RuleStatus.TRIGGERED,
                risk_points=round(points, 1),
                reason=f"{count_5m} transactions occurred within the last 5 minutes.",
                evidence=evidence,
                mitigation=None,
            )

        if count_1h > self.threshold_1h:
            if is_mitigated:
                return RuleResult(
                    rule_name=self.name,
                    status=RuleStatus.MITIGATED,
                    risk_points=10.0,
                    reason=f"{count_1h} transactions occurred within the last 1 hour (mitigated by authorized bulk status).",
                    evidence=evidence,
                    mitigation=mitigation_reason,
                )
            excess = count_1h - self.threshold_1h
            points = min(85.0, self.risk_points_1h + (excess * 3.0))
            return RuleResult(
                rule_name=self.name,
                status=RuleStatus.TRIGGERED,
                risk_points=round(points, 1),
                reason=f"{count_1h} transactions occurred within the last 1 hour.",
                evidence=evidence,
                mitigation=None,
            )

        if count_today > self.threshold_today:
            return RuleResult(
                rule_name=self.name,
                status=RuleStatus.TRIGGERED,
                risk_points=self.risk_points_today,
                reason=f"{count_today} transactions occurred today (threshold: {self.threshold_today}).",
                evidence=evidence,
                mitigation=None,
            )

        return RuleResult(
            rule_name=self.name,
            status=RuleStatus.NORMAL,
            risk_points=0.0,
            reason=f"Transaction velocity is within normal limits ({count_5m} in last 5m, {count_1h} in last 1h).",
            evidence=evidence,
            mitigation=None,
        )
