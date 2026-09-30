"""Hybrid Explainable Fraud Risk Detection & Review Platform - Main Application."""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Hybrid Explainable Fraud Risk Detection & Review Platform")
APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    # Startup actions
    yield
    # Shutdown actions


app = FastAPI(
    title=APP_NAME,
    description="Hybrid Explainable Fraud Risk Detection & Review Platform API",
    version="0.1.0",
    debug=DEBUG,
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix="/api")
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint verifying API availability and status."""
    return {
        "status": "online",
        "service": APP_NAME,
        "environment": APP_ENV,
        "version": "0.1.0",
        "docs_url": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": APP_NAME,
    }
