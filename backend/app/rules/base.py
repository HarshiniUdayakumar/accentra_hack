"""Base interfaces and models for the modular fraud rule engine.

Every rule inherits from BaseRule and outputs a standardized RuleResult.
Rules produce risk signals (NORMAL, TRIGGERED, MITIGATED) and must not
return a definitive 'fraud' verdict.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RuleStatus(str, Enum):
    """Permitted evaluation status values for a fraud rule."""

    NORMAL = "NORMAL"
    TRIGGERED = "TRIGGERED"
    MITIGATED = "MITIGATED"


class RuleResult(BaseModel):
    """Standardized result returned by every fraud detection rule component."""

    rule_name: str
    status: RuleStatus = RuleStatus.NORMAL
    risk_points: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Risk contribution (0.0 to 100.0)"
    )
    reason: str = Field(default="", description="Human-readable explanation of result")
    evidence: Dict[str, Any] = Field(
        default_factory=dict, description="Supporting numerical and contextual data"
    )
    mitigation: Optional[str] = Field(
        default=None, description="Explanation if a legitimate exception mitigated the risk"
    )

    @property
    def triggered(self) -> bool:
        """Helper boolean indicating if the rule triggered."""
        return self.status == RuleStatus.TRIGGERED

    @property
    def risk_score(self) -> float:
        """Alias for risk_points to maintain compatibility with legacy callers."""
        return self.risk_points


class BaseRule(ABC):
    """Abstract base class for all detection rules.

    Each rule encapsulates its own thresholds, heuristics, and explanation logic.
    New rules (e.g. DeviceRule, MerchantRule) can be added without modifying the engine.
    """

    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight

    @abstractmethod
    def evaluate(
        self,
        transaction: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RuleResult:
        """Evaluate an incoming transaction against this rule.

        Args:
            transaction: Current incoming transaction dictionary.
            history: Optional list of previous customer transactions ordered descending by timestamp.
            context: Optional contextual flags or customer profile metadata.

        Returns:
            Standardized RuleResult with status, risk_points, reason, evidence, and mitigation.
        """
        pass


def to_dict(obj: Any) -> Dict[str, Any]:
    """Convert a Pydantic model or mapping to a standard Python dictionary."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    elif hasattr(obj, "dict"):
        return obj.dict()
    elif isinstance(obj, dict):
        return dict(obj)
    return dict(obj)


def parse_timestamp(dt_val: Any):
    """Parse a datetime, date, or ISO string into a timezone-naive datetime object."""
    from datetime import date, datetime

    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is not None:
            return dt_val.replace(tzinfo=None)
        return dt_val
    if isinstance(dt_val, date):
        return datetime(dt_val.year, dt_val.month, dt_val.day)
    if isinstance(dt_val, str):
        clean_str = dt_val.replace("Z", "").split("+")[0]
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(clean_str, fmt)
            except ValueError:
                continue
        dt = datetime.fromisoformat(dt_val)
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
    raise ValueError(f"Cannot parse datetime from value: {dt_val}")

