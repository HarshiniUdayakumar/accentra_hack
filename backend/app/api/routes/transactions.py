"""Transaction API route endpoints."""
from fastapi import APIRouter, HTTPException, status
from app.schemas.transaction import TransactionCreate, TransactionProcessResponse
from app.services.transaction_service import process_new_transaction

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post(
    "",
    response_model=TransactionProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive new transaction and retrieve customer history",
    description=(
        "Accepts an incoming transaction payload, validates fields, and automatically "
        "retrieves the customer's previous transaction history from MySQL for downstream "
        "fraud and anomaly analysis."
    ),
)
async def create_transaction(transaction: TransactionCreate):
    """Process incoming transaction and fetch customer transaction history."""
    try:
        response = process_new_transaction(transaction=transaction)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the transaction: {str(e)}",
        )
