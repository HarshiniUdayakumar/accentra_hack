"""Transaction Pydantic schemas for request validation and response formatting."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class TransactionCreate(BaseModel):
    """Schema for incoming transaction payload."""

    transaction_id: str = Field(
        ..., min_length=1, description="Unique transaction identifier"
    )
    customer_id: str = Field(
        ..., min_length=1, description="Customer identifier"
    )
    amount: float = Field(
        ..., gt=0, description="Transaction amount (must be greater than 0)"
    )
    timestamp: datetime = Field(
        ..., description="Timestamp of the transaction (ISO format)"
    )
    latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude coordinate between -90 and 90"
    )
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude coordinate between -180 and 180"
    )
    location_name: str = Field(
        ..., min_length=1, description="City or location name"
    )
    merchant: str = Field(
        ..., min_length=1, description="Merchant or recipient entity"
    )
    transaction_type: str = Field(
        ..., min_length=1, description="Transaction type (e.g. PURCHASE, PAYMENT, TRANSFER)"
    )
    channel: str = Field(
        ..., min_length=1, description="Channel used (e.g. UPI, POS, NET_BANKING)"
    )

    @field_validator(
        "transaction_id",
        "customer_id",
        "location_name",
        "merchant",
        "transaction_type",
        "channel",
    )
    @classmethod
    def check_non_empty(cls, value: str) -> str:
        """Ensure string fields are not purely whitespace."""
        if not value or not value.strip():
            raise ValueError("Field cannot be empty or blank")
        return value.strip()


class CustomerHistory(BaseModel):
    """Customer previous transaction history summary."""

    customer_id: str
    transaction_count: int
    transactions: List[Dict[str, Any]] = Field(default_factory=list)


class TransactionProcessResponse(BaseModel):
    """API response schema for processed incoming transaction."""

    message: str
    transaction: TransactionCreate
    customer_history: CustomerHistory
    rule_results: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="RuleResult objects from evaluated fraud rules"
    )

