from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.transaction import TransactionCreate, TransactionProcessResponse
from app.services.transaction_service import (
    process_new_transaction,
    transaction_service,
    get_history,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List recent transactions",
    description="Retrieve recent transactions across customers from the database for dashboard display.",
)
async def list_transactions(
    limit: int = Query(default=50, ge=1, le=500),
    customer_id: Optional[str] = Query(default=None),
):
    """Retrieve recent transactions with optional customer filtering."""
    try:
        if customer_id:
            records = get_history(customer_id=customer_id, limit=limit)
        else:
            records = transaction_service.get_recent_transactions(limit=limit)
        return {"count": len(records), "transactions": records}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch transactions: {str(e)}",
        )


@router.post(
    "",
    response_model=TransactionProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive new transaction and retrieve customer history",
    description=(
        "Accepts an incoming transaction payload, validates fields, automatically "
        "retrieves customer history, and evaluates registered fraud rules."
    ),
)
async def create_transaction(transaction: TransactionCreate):
    """Process incoming transaction, fetch customer history, and evaluate rules."""
    try:
        response = process_new_transaction(transaction=transaction)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the transaction: {str(e)}",
        )

