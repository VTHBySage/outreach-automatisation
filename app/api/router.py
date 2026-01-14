"""Main API router aggregation."""

from fastapi import APIRouter

from app.api.health.router import router as health_router
from app.api.v1 import router as v1_router
from app.api.webhooks.router import router as webhook_router

api_router = APIRouter()

# Health endpoints at root
api_router.include_router(health_router, tags=["health"])

# Webhook endpoints
api_router.include_router(webhook_router, prefix="/webhook", tags=["webhooks"])

# API v1 endpoints
api_router.include_router(v1_router, prefix="/api/v1")
