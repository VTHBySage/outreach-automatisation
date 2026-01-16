"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import settings
from app.core.logging import setup_logging
from app.db.session import engine
from app.middleware.audit import AuditMiddleware

# Initialize Sentry for error tracking (before app creation)
if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment or settings.app_env,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[
            FastApiIntegration(),
            CeleryIntegration(),
        ],
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging()

    # Initialize database connection pool
    # Connection is established on first query

    yield

    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Outreach Automation API",
        description="Multichannel B2B outreach automation system",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Audit logging middleware (logs all API requests)
    app.add_middleware(
        AuditMiddleware,
        log_to_db=True,
        log_to_stdout=settings.app_debug,
    )

    # Include routers
    app.include_router(api_router)

    # Serve static dashboard UI
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/dashboard", include_in_schema=False)
        async def dashboard():
            """Serve the dashboard UI."""
            return FileResponse(static_dir / "dashboard.html")

    return app


app = create_app()
