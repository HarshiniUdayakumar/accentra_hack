"""API route definitions and router registration."""
from fastapi import APIRouter
from app.api.routes.transactions import router as transactions_router

api_router = APIRouter()

# Mount route modules
api_router.include_router(transactions_router)

__all__ = ["api_router"]
