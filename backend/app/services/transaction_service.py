"""Transaction orchestration service and customer history retrieval.

Coordinates incoming transaction acceptance, automatic customer history lookup,
and prepares data for future fraud scoring pipelines without persisting prematurely.
"""
from typing import Any, Dict, List, Optional
from app.database.connection import get_customer_history
from app.schemas.transaction import (
    CustomerHistory,
    TransactionCreate,
    TransactionProcessResponse,
)


def get_history(customer_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve historical transactions for a customer ordered by timestamp descending.

    Args:
        customer_id: Customer ID (e.g. 'C101').
        limit: Maximum number of transactions to retrieve.

    Returns:
        List of transaction dictionaries.
    """
    return get_customer_history(customer_id=customer_id, limit=limit)


def process_new_transaction(
    transaction: TransactionCreate, history_limit: int = 100
) -> TransactionProcessResponse:
    """Accept an incoming transaction and automatically retrieve customer history.

    Args:
        transaction: Validated incoming TransactionCreate payload.
        history_limit: Maximum historical records to fetch (default: 100).

    Returns:
        TransactionProcessResponse containing transaction details, history, and status message.
    """
    history_records = get_history(customer_id=transaction.customer_id, limit=history_limit)
    count = len(history_records)

    if count == 0:
        message = (
            f"Transaction received. No previous history found for customer '{transaction.customer_id}'."
        )
    else:
        message = "Transaction received and customer history retrieved successfully."

    customer_history = CustomerHistory(
        customer_id=transaction.customer_id,
        transaction_count=count,
        transactions=history_records,
    )

    return TransactionProcessResponse(
        message=message,
        transaction=transaction,
        customer_history=customer_history,
    )


def evaluate_transaction_rules(
    transaction: Any,
    history: Optional[List[Dict[str, Any]]] = None,
    context: Optional[Dict[str, Any]] = None,
    engine: Optional[Any] = None,
    history_limit: int = 100,
) -> List[Any]:
    """Evaluate fraud detection rules for an incoming transaction.

    Orchestrates the pipeline: Database -> Service -> Rule Engine -> Rules.
    If history is not explicitly supplied, retrieves it via the database repository.

    Args:
        transaction: TransactionCreate model or dictionary.
        history: Optional pre-loaded customer history records.
        context: Optional evaluation context or whitelist flags.
        engine: Optional customized RuleEngine instance.
        history_limit: Max historical records to retrieve if fetching from DB.

    Returns:
        List of RuleResult objects from evaluated rules.
    """
    from app.rules.engine import RuleEngine
    from app.rules.base import to_dict

    txn_dict = to_dict(transaction)
    customer_id = txn_dict.get("customer_id")

    if history is None and customer_id:
        history = get_history(customer_id=str(customer_id), limit=history_limit)

    active_engine = engine or RuleEngine()
    return active_engine.evaluate_all(
        transaction=txn_dict, history=history, context=context
    )


class TransactionService:
    """Handles transaction ingestion, history retrieval, and analysis workflow."""

    def __init__(self) -> None:
        pass

    def get_history(self, customer_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve customer transaction history."""
        return get_history(customer_id=customer_id, limit=limit)

    def process_new_transaction(
        self, transaction: TransactionCreate, history_limit: int = 100
    ) -> TransactionProcessResponse:
        """Process incoming transaction and attach customer history."""
        return process_new_transaction(transaction=transaction, history_limit=history_limit)

    def evaluate_rules(
        self,
        transaction: Any,
        history: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
        engine: Optional[Any] = None,
        history_limit: int = 100,
    ) -> List[Any]:
        """Evaluate fraud detection rules via RuleEngine."""
        return evaluate_transaction_rules(
            transaction=transaction,
            history=history,
            context=context,
            engine=engine,
            history_limit=history_limit,
        )

    def process_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy placeholder for dict-based processing."""
        return {
            "transaction_id": transaction_data.get("id", "placeholder"),
            "status": "received",
        }


# Global service instance
transaction_service = TransactionService()

