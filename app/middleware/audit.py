"""Audit logging middleware for tracking all API actions."""

import json
import time
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4

from fastapi import Request, Response
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger
from app.db.base import Base, TimestampMixin, UUIDMixin

logger = get_logger(__name__)


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Database model for audit log entries."""

    __tablename__ = "audit_logs"

    # Request info
    request_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    query_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # User/client info
    client_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)

    # Request body (sanitized - no sensitive data)
    request_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Response info
    status_code: Mapped[int | None] = mapped_column(nullable=True)
    response_time_ms: Mapped[float | None] = mapped_column(nullable=True)

    # Error info
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp for the action
    action_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False, index=True
    )


# Fields to exclude from audit logs (sensitive data)
SENSITIVE_FIELDS = {
    "password",
    "token",
    "secret",
    "api_key",
    "access_token",
    "refresh_token",
    "authorization",
    "credit_card",
    "ssn",
    "social_security",
}

# Paths to skip auditing
SKIP_PATHS = {
    "/health",
    "/health/ready",
    "/health/live",
    "/health/metrics",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def sanitize_data(data: Any, depth: int = 0, max_depth: int = 5) -> Any:
    """
    Recursively sanitize data by masking sensitive fields.

    Args:
        data: Data to sanitize
        depth: Current recursion depth
        max_depth: Maximum recursion depth

    Returns:
        Sanitized data
    """
    if depth > max_depth:
        return "[MAX_DEPTH_EXCEEDED]"

    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if any(s in key.lower() for s in SENSITIVE_FIELDS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_data(value, depth + 1, max_depth)
        return sanitized

    elif isinstance(data, list):
        return [sanitize_data(item, depth + 1, max_depth) for item in data[:100]]

    elif isinstance(data, str) and len(data) > 1000:
        return data[:1000] + "...[TRUNCATED]"

    return data


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive audit logging of all API requests.

    Logs:
    - Request method, path, query params
    - Client IP, user agent
    - Request body (sanitized)
    - Response status code
    - Response time
    - Errors
    """

    def __init__(
        self,
        app: ASGIApp,
        log_to_db: bool = True,
        log_to_stdout: bool = True,
    ):
        super().__init__(app)
        self.log_to_db = log_to_db
        self.log_to_stdout = log_to_stdout

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        # Skip auditing for certain paths
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        # Generate request ID
        request_id = str(uuid4())[:8]
        start_time = time.time()
        error_message = None

        # Extract request info
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")[:500]

        # Try to get request body (only for certain methods)
        request_body = None
        if method in {"POST", "PUT", "PATCH"}:
            try:
                body = await request.body()
                if body:
                    request_body = sanitize_data(json.loads(body.decode()))
            except Exception:
                request_body = {"_error": "Could not parse body"}

        # Process request
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        except Exception as e:
            error_message = str(e)[:1000]
            raise

        finally:
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000

            # Record Prometheus metrics
            try:
                from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY

                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=path,
                    status=str(status_code),
                ).inc()
                REQUEST_LATENCY.labels(
                    method=method,
                    endpoint=path,
                ).observe(response_time_ms / 1000)  # Convert to seconds
            except Exception:
                pass  # Don't fail request if metrics fail

            # Log to stdout
            if self.log_to_stdout:
                logger.info(
                    "audit_log",
                    request_id=request_id,
                    method=method,
                    path=path,
                    status_code=status_code,
                    response_time_ms=round(response_time_ms, 2),
                    client_ip=client_ip,
                    error=error_message,
                )

            # Log to database (async - don't block response)
            if self.log_to_db:
                try:
                    await self._log_to_database(
                        request_id=request_id,
                        method=method,
                        path=path,
                        query_params=query_params,
                        client_ip=client_ip,
                        user_agent=user_agent,
                        request_body=request_body,
                        status_code=status_code,
                        response_time_ms=response_time_ms,
                        error_message=error_message,
                    )
                except Exception as e:
                    logger.error("audit_log_db_error", error=str(e))

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers or connection."""
        # Check X-Forwarded-For header (for proxied requests)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to connection client
        if request.client:
            return request.client.host

        return "unknown"

    async def _log_to_database(
        self,
        request_id: str,
        method: str,
        path: str,
        query_params: dict | None,
        client_ip: str | None,
        user_agent: str | None,
        request_body: dict | None,
        status_code: int,
        response_time_ms: float,
        error_message: str | None,
    ) -> None:
        """Save audit log entry to database."""
        from app.db.session import async_session_factory

        async with async_session_factory() as session:
            try:
                audit_log = AuditLog(
                    request_id=request_id,
                    method=method,
                    path=path,
                    query_params=query_params,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    request_body=request_body,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    action_at=datetime.utcnow(),
                )
                session.add(audit_log)
                await session.commit()

            except Exception as e:
                await session.rollback()
                logger.error("audit_log_save_failed", error=str(e))


class AuditLogService:
    """Service for querying audit logs."""

    def __init__(self, session):
        self.session = session

    async def get_logs_for_path(
        self,
        path: str,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit logs for a specific path."""
        from sqlalchemy import select

        stmt = (
            select(AuditLog)
            .where(AuditLog.path.like(f"{path}%"))
            .order_by(AuditLog.action_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_logs_for_user(
        self,
        user_id: str,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit logs for a specific user."""
        from sqlalchemy import select

        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.action_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_error_logs(
        self,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit logs with errors."""
        from sqlalchemy import select

        stmt = (
            select(AuditLog)
            .where(AuditLog.status_code >= 400)
            .order_by(AuditLog.action_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_slow_requests(
        self,
        threshold_ms: float = 1000,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get slow request audit logs."""
        from sqlalchemy import select

        stmt = (
            select(AuditLog)
            .where(AuditLog.response_time_ms > threshold_ms)
            .order_by(AuditLog.response_time_ms.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
