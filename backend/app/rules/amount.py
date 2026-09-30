"""Unusual transaction amount detection rule component.

Evaluates an incoming transaction's monetary value against the customer's personal
historical spending profile (average, maximum, standard deviation, and deviation).
Recognizes that high amounts are not inherently fraudulent if consistent with customer history.
"""
import math
from typing import Any, Dict, List, Optional
from app.rules.base import BaseRule, RuleResult, RuleStatus, to_dict


class AmountRule(BaseRule):
    """Detects transactions with amounts deviating significantly from user's historical norms."""

    def __init__(
        self,
        name: str = "AmountRule",
        weight: float = 1.0,
        multiplier_threshold: float = 3.0,
        z_score_threshold: float = 3.0,
        min_history_for_std: int = 3,
        base_risk_points: float = 75.0,
    ):
        """Initialize AmountRule with configurable behavioral thresholds.

        Args:
            name: Rule identifier.
            weight: Relative rule weight.
            multiplier_threshold: Factor over historical average considered anomalous (default: 3.0).
            z_score_threshold: Standard deviations above mean considered anomalous (default: 3.0).
            min_history_for_std: Minimum historical records required for z-score calculation (default: 3).
            base_risk_points: Base risk contribution when triggered (default: 75.0).
        """
        super().__init__(name=name, weight=weight)
        self.multiplier_threshold = multiplier_threshold
        self.z_score_threshold = z_score_threshold
        self.min_history_for_std = min_history_for_std
        self.base_risk_points = base_risk_points

    def evaluate(
        self,
        transaction: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RuleResult:
        """Evaluate incoming transaction amount against customer historical amounts.

        Args:
            transaction: Current transaction payload or dictionary.
            history: Optional list of previous customer transactions.
            context: Optional contextual parameters (e.g. pre-authorization flags).

        Returns:
            RuleResult with amount statistics, deviation metrics, status, and reason.
        """
        txn_dict = to_dict(transaction)
        customer_id = str(txn_dict.get("customer_id", "Unknown"))
        current_amount = float(txn_dict.get("amount", 0.0))

        # Extract historical amounts
        hist_amounts: List[float] = []
        if history:
            for h in history:
                h_dict = to_dict(h)
                # Ignore current transaction if present in history
                if txn_dict.get("transaction_id") and h_dict.get("transaction_id") == txn_dict.get("transaction_id"):
                    continue

                amt = h_dict.get("amount")
                if amt is not None:
                    try:
                        hist_amounts.append(float(amt))
                    except (ValueError, TypeError):
                        continue

        # If no history exists, we cannot establish an anomalous deviation baseline
        if not hist_amounts:
            return RuleResult(
                rule_name=self.name,
                status=RuleStatus.NORMAL,
                risk_points=0.0,
                reason=(
                    f"No previous transaction history available for customer '{customer_id}' "
                    f"to establish an amount baseline."
                ),
                evidence={
                    "current_amount": round(current_amount, 2),
                    "historical_count": 0,
                    "customer_id": customer_id,
                },
                mitigation=None,
            )

        hist_avg = sum(hist_amounts) / len(hist_amounts)
        hist_max = max(hist_amounts)
        hist_min = min(hist_amounts)
        amount_deviation = current_amount - hist_avg
        multiplier = current_amount / hist_avg if hist_avg > 0 else 0.0

        if len(hist_amounts) >= self.min_history_for_std:
            variance = sum((x - hist_avg) ** 2 for x in hist_amounts) / len(hist_amounts)
            hist_std = math.sqrt(variance)
            z_score = (current_amount - hist_avg) / hist_std if hist_std > 0 else 0.0
        else:
            hist_std = 0.0
            z_score = 0.0

        evidence: Dict[str, Any] = {
            "current_amount": round(current_amount, 2),
            "historical_average": round(hist_avg, 2),
            "historical_maximum": round(hist_max, 2),
            "historical_minimum": round(hist_min, 2),
            "historical_std_dev": round(hist_std, 2),
            "amount_deviation": round(amount_deviation, 2),
            "multiplier_of_average": round(multiplier, 2),
            "z_score": round(z_score, 2),
            "threshold_multiplier": self.multiplier_threshold,
            "threshold_z_score": self.z_score_threshold,
            "history_count": len(hist_amounts),
            "customer_id": customer_id,
        }

        # Check for context mitigation (e.g. pre-authorized large purchase)
        is_mitigated = False
        mitigation_reason: Optional[str] = None
        if context:
            if context.get("is_pre_authorized") or context.get("high_value_exempt"):
                is_mitigated = True
                mitigation_reason = (
                    f"Transaction amount of Rs.{current_amount:,.2f} is pre-authorized by customer or credit limit."
                )

        # Core behavioral rule:
        # A high amount is NOT fraud if it falls within the customer's historical range.
        if current_amount <= hist_max:
            return RuleResult(
                rule_name=self.name,
                status=RuleStatus.NORMAL,
                risk_points=0.0,
                reason=(
                    f"Current amount (Rs.{current_amount:,.2f}) is within customer's normal historical "
                    f"spending behavior (average: Rs.{hist_avg:,.2f}, maximum: Rs.{hist_max:,.2f})."
                ),
                evidence=evidence,
                mitigation=None,
            )

        # Current amount exceeds historical maximum. Evaluate if deviation is statistically significant.
        is_anomalous = (multiplier >= self.multiplier_threshold) or (
            hist_std > 0 and z_score >= self.z_score_threshold
        )

        if is_anomalous:
            if is_mitigated:
                return RuleResult(
                    rule_name=self.name,
                    status=RuleStatus.MITIGATED,
                    risk_points=20.0,
                    reason=(
                        f"Amount Rs.{current_amount:,.2f} significantly exceeds historical average (Rs.{hist_avg:,.2f}) "
                        f"but has been pre-authorized."
                    ),
                    evidence=evidence,
                    mitigation=mitigation_reason,
                )

            # Scale risk points based on how extreme the deviation is (capped at 95.0)
            points = min(95.0, self.base_risk_points + min(20.0, (multiplier - self.multiplier_threshold) * 2.0))
            return RuleResult(
                rule_name=self.name,
                status=RuleStatus.TRIGGERED,
                risk_points=round(points, 1),
                reason=(
                    f"Transaction amount of Rs.{current_amount:,.2f} is significantly unusual: "
                    f"{multiplier:.1f}x higher than customer's historical average of Rs.{hist_avg:,.2f} "
                    f"and exceeds previous maximum of Rs.{hist_max:,.2f} (z-score: {z_score:.2f})."
                ),
                evidence=evidence,
                mitigation=None,
            )

        # Amount slightly exceeds maximum but is not significantly anomalous
        return RuleResult(
            rule_name=self.name,
            status=RuleStatus.NORMAL,
            risk_points=0.0,
            reason=(
                f"Amount Rs.{current_amount:,.2f} slightly exceeds historical maximum Rs.{hist_max:,.2f}, "
                f"but deviation remains within acceptable behavioral bounds ({multiplier:.1f}x average)."
            ),
            evidence=evidence,
            mitigation=None,
        )
