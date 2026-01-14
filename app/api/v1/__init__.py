"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.contacts import router as contacts_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.gdpr import router as gdpr_router
from app.api.v1.tasks import router as tasks_router

router = APIRouter()

router.include_router(contacts_router, prefix="/contacts", tags=["contacts"])
router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
router.include_router(gdpr_router, prefix="/gdpr", tags=["gdpr"])
