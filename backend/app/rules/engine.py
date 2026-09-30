"""Modular rule engine orchestrator.

Coordinates execution of registered BaseRule instances across transaction payloads
and customer history records. Contains no rule-specific heuristics, ensuring full
modularity and decoupling: new rules (e.g. DeviceRule, MerchantRule) can be attached
without altering engine or existing rule code.
"""
from typing import Any, Dict, List, Optional
from app.rules.base import BaseRule, RuleResult


class RuleEngine:
    """Orchestrates the evaluation of registered fraud detection rules."""

    def __init__(self, rules: Optional[List[BaseRule]] = None):
        """Initialize RuleEngine.

        Args:
            rules: Optional list of BaseRule instances. If None, registers the three default rules:
                   VelocityRule, AmountRule, and LocationRule.
        """
        if rules is None:
            from app.rules.amount import AmountRule
            from app.rules.location import LocationRule
            from app.rules.velocity import VelocityRule

            self._rules: List[BaseRule] = [
                VelocityRule(),
                AmountRule(),
                LocationRule(),
            ]
        else:
            self._rules = list(rules)

    def register_rule(self, rule: BaseRule) -> None:
        """Register a new detection rule component."""
        self._rules.append(rule)

    def unregister_rule(self, rule_name: str) -> None:
        """Unregister a rule by name."""
        self._rules = [r for r in self._rules if r.name != rule_name]

    @property
    def registered_rules(self) -> List[str]:
        """Return names of all currently registered rule components."""
        return [rule.name for rule in self._rules]

    def evaluate_all(
        self,
        transaction: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RuleResult]:
        """Execute all registered rules against the transaction and history.

        Args:
            transaction: Transaction dictionary or payload to evaluate.
            history: Optional list of previous customer transactions.
            context: Optional contextual data or metadata.

        Returns:
            List of standardized RuleResult objects from each evaluated rule.
        """
        results: List[RuleResult] = []
        for rule in self._rules:
            result = rule.evaluate(transaction=transaction, history=history, context=context)
            results.append(result)
        return results
