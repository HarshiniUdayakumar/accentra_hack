"""Geographical anomaly detection rule component.

Evaluates physical movement feasibility by calculating Haversine distance, elapsed time,
and implied travel speed between consecutive transactions. Supports explainable mitigation
for registered multi-location business travelers (e.g. C102, C104) and contextual exceptions.
"""
import math
from typing import Any, Dict, List, Optional, Set
from app.rules.base import BaseRule, RuleResult, RuleStatus, parse_timestamp, to_dict


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two coordinates in kilometers."""
    r = 6371.0  # Mean radius of Earth in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


# Default set of customers with legitimate multi-location business/travel behavior
DEFAULT_LEGITIMATE_MULTI_LOCATION_CUSTOMERS: Set[str] = {"C102", "C104"}

# Known legitimate hubs for specific traveler profiles
DEFAULT_CUSTOMER_KNOWN_LOCATIONS: Dict[str, Set[str]] = {
    "C102": {"Chennai", "Bangalore", "Mumbai"},
    "C104": {"Bangalore", "Hyderabad", "Chennai"},
}


class LocationRule(BaseRule):
    """Detects geographical anomalies such as physically implausible travel speeds."""

    def __init__(
        self,
        name: str = "LocationRule",
        weight: float = 1.0,
        max_speed_kmh: float = 800.0,
        min_distance_km: float = 15.0,
        base_risk_points: float = 85.0,
        legitimate_multi_location_customers: Optional[Set[str]] = None,
        known_customer_locations: Optional[Dict[str, Set[str]]] = None,
    ):
        """Initialize LocationRule with speed limits and whitelisted traveler profiles.

        Args:
            name: Rule identifier.
            weight: Relative rule weight.
            max_speed_kmh: Implied speed threshold above which movement is physically implausible (default: 800.0 km/h).
            min_distance_km: Minimum distance required before evaluating speed anomaly (default: 15.0 km).
            base_risk_points: Risk points assigned when triggered without mitigation (default: 85.0).
            legitimate_multi_location_customers: Set of customer IDs exempt from blind triggers.
            known_customer_locations: Mapping of customer IDs to sets of authorized/known location names.
        """
        super().__init__(name=name, weight=weight)
        self.max_speed_kmh = max_speed_kmh
        self.min_distance_km = min_distance_km
        self.base_risk_points = base_risk_points
        self.legitimate_customers = (
            set(legitimate_multi_location_customers)
            if legitimate_multi_location_customers is not None
            else set(DEFAULT_LEGITIMATE_MULTI_LOCATION_CUSTOMERS)
        )
        self.known_locations = (
            dict(known_customer_locations)
            if known_customer_locations is not None
            else dict(DEFAULT_CUSTOMER_KNOWN_LOCATIONS)
        )

    def evaluate(
        self,
        transaction: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RuleResult:
        """Evaluate geographical plausibility between current and previous transactions.

        Args:
            transaction: Current transaction payload or dictionary.
            history: Optional list of previous customer transactions.
            context: Optional contextual parameters (e.g. travel whitelist or account context).

        Returns:
            RuleResult with distance, time elapsed, implied speed, status, and reason.
        """
        txn_dict = to_dict(transaction)
        customer_id = str(txn_dict.get("customer_id", "Unknown"))
        current_tx_id = txn_dict.get("transaction_id")

        try:
            curr_lat = float(txn_dict["latitude"])
            curr_lon = float(txn_dict["longitude"])
            curr_loc_name = str(txn_dict.get("location_name", "Unknown"))
            current_time = parse_timestamp(txn_dict["timestamp"])
        except Exception as e:
            return RuleResult(
                rule_name=self.name,
                status=RuleStatus.NORMAL,
                risk_points=0.0,
                reason=f"Unable to evaluate location due to missing or invalid coordinates/timestamp: {e}",
                evidence={"error": str(e), "customer_id": customer_id},
                mitigation=None,
            )

        # Locate the most recent historical transaction with valid location strictly prior to current
        prev_txn: Optional[Dict[str, Any]] = None
        prev_time = None
        prev_lat = 0.0
        prev_lon = 0.0
        prev_loc_name = "Unknown"

        # Also collect historical locations to identify established customer hubs
        historical_cities: Set[str] = set()

        if history:
            valid_priors: List[tuple] = []
            for h in history:
                h_dict = to_dict(h)
                if current_tx_id and h_dict.get("transaction_id") == current_tx_id:
                    continue

                h_loc = h_dict.get("location_name")
                if h_loc:
                    historical_cities.add(str(h_loc).strip())

                if "latitude" not in h_dict or "longitude" not in h_dict or "timestamp" not in h_dict:
                    continue

                try:
                    h_time = parse_timestamp(h_dict["timestamp"])
                    h_lat = float(h_dict["latitude"])
                    h_lon = float(h_dict["longitude"])
                except Exception:
                    continue

                if h_time <= current_time:
                    valid_priors.append((h_time, h_dict, h_lat, h_lon))

            if valid_priors:
                # Sort descending by timestamp to obtain the immediately preceding transaction
                valid_priors.sort(key=lambda x: x[0], reverse=True)
                prev_time, prev_txn, prev_lat, prev_lon = valid_priors[0]
                prev_loc_name = str(prev_txn.get("location_name", "Unknown"))

        # If no prior location exists in history, we cannot establish geographical speed
        if prev_txn is None or prev_time is None:
            return RuleResult(
                rule_name=self.name,
                status=RuleStatus.NORMAL,
                risk_points=0.0,
                reason=(
                    f"No previous transaction location found for customer '{customer_id}' "
                    f"to establish travel trajectory."
                ),
                evidence={
                    "current_location": curr_loc_name,
                    "previous_location": None,
                    "customer_id": customer_id,
                },
                mitigation=None,
            )

        # Calculate Haversine distance, elapsed time, and implied speed
        distance_km = haversine_distance_km(prev_lat, prev_lon, curr_lat, curr_lon)
        delta_seconds = (current_time - prev_time).total_seconds()

        # Handle edge cases of identical timestamps or sub-second intervals
        if delta_seconds < 1.0:
            delta_seconds = 1.0

        time_diff_minutes = delta_seconds / 60.0
        time_diff_hours = delta_seconds / 3600.0
        implied_speed_kmh = distance_km / time_diff_hours

        evidence: Dict[str, Any] = {
            "previous_location": prev_loc_name,
            "previous_location_details": {
                "name": prev_loc_name,
                "latitude": round(prev_lat, 4),
                "longitude": round(prev_lon, 4),
                "timestamp": prev_time.isoformat(),
            },
            "current_location": curr_loc_name,
            "current_location_details": {
                "name": curr_loc_name,
                "latitude": round(curr_lat, 4),
                "longitude": round(curr_lon, 4),
                "timestamp": current_time.isoformat(),
            },
            "distance_km": round(distance_km, 2),
            "time_difference_minutes": round(time_diff_minutes, 2),
            "implied_speed_kmh": round(implied_speed_kmh, 2),
            "speed_threshold_kmh": self.max_speed_kmh,
            "customer_id": customer_id,
        }

        # Check for implausible physical travel
        is_implausible = (distance_km > self.min_distance_km) and (
            implied_speed_kmh > self.max_speed_kmh
        )

        if not is_implausible:
            return RuleResult(
                rule_name=self.name,
                status=RuleStatus.NORMAL,
                risk_points=0.0,
                reason=(
                    f"Geographical movement is consistent with elapsed time "
                    f"({distance_km:.1f} km over {time_diff_minutes:.1f} minutes, "
                    f"implied speed: {implied_speed_kmh:.1f} km/h)."
                ),
                evidence=evidence,
                mitigation=None,
            )

        # Implausible speed detected! Now evaluate whether a legitimate mitigation applies.
        is_legitimate_customer = customer_id in self.legitimate_customers
        context_override = False
        if context:
            if context.get("is_multi_location_whitelisted") or context.get("legitimate_multi_location"):
                context_override = True

        # Build complete set of authorized locations for this customer
        known_hubs = set(self.known_locations.get(customer_id, set()))
        known_hubs.update(historical_cities)

        # Check if customer travels between authorized locations
        travels_between_known = (
            curr_loc_name in known_hubs or prev_loc_name in known_hubs
        )

        if (is_legitimate_customer and travels_between_known) or context_override:
            mitigation_text = (
                f"Customer '{customer_id}' is recognized in configured legitimate multi-location "
                f"profiles ({prev_loc_name} <-> {curr_loc_name}). Anomaly mitigated."
            )
            return RuleResult(
                rule_name=self.name,
                status=RuleStatus.MITIGATED,
                risk_points=20.0,
                reason=(
                    f"Geographical movement speed is high ({implied_speed_kmh:,.1f} km/h), "
                    f"but customer has legitimate multi-location authorization."
                ),
                evidence=evidence,
                mitigation=mitigation_text,
            )

        # No legitimate exception applies -> Generate risk signal
        return RuleResult(
            rule_name=self.name,
            status=RuleStatus.TRIGGERED,
            risk_points=self.base_risk_points,
            reason="Geographical movement is inconsistent with the elapsed time.",
            evidence=evidence,
            mitigation=None,
        )
