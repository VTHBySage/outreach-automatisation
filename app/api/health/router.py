"""Health check endpoints."""

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.db.session import async_session_factory

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Basic health check - returns immediately."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check(response: Response) -> dict:
    """Readiness check - verifies all dependencies."""
    checks = {
        "database": False,
        "redis": False,
    }

    # Check database
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            checks["database"] = True
    except Exception:
        pass

    # Check Redis (via Celery)
    try:
        from app.workers.celery_app import celery_app

        celery_app.control.ping(timeout=1)
        checks["redis"] = True
    except Exception:
        pass

    # Determine overall status
    all_healthy = all(checks.values())
    if not all_healthy:
        response.status_code = 503

    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
    }


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Prometheus metrics endpoint for monitoring."""
    from app.core.metrics import generate_latest, CONTENT_TYPE_LATEST

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
