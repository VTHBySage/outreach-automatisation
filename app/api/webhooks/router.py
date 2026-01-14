"""Webhook router aggregation."""

from fastapi import APIRouter

from app.api.webhooks.connectsafely import router as connectsafely_router
from app.api.webhooks.smartlead import router as smartlead_router

router = APIRouter()

router.include_router(smartlead_router, prefix="/smartlead")
router.include_router(connectsafely_router, prefix="/connectsafely")
