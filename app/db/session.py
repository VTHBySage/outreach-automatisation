"""Database session configuration with performance monitoring."""

import time
from contextvars import ContextVar

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.logging import get_logger
from app.core.metrics import (
    DB_CONNECTION_POOL_CHECKED_OUT,
    DB_CONNECTION_POOL_SIZE,
    DB_QUERY_DURATION,
    DB_SLOW_QUERIES,
)

logger = get_logger(__name__)

# Context var to store query start time
_query_start_time: ContextVar[float] = ContextVar("query_start_time", default=0.0)

# Slow query threshold in seconds
SLOW_QUERY_THRESHOLD = 0.1  # 100ms


# Create async engine
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.app_debug,
    pool_pre_ping=True,
    pool_recycle=settings.database_pool_recycle,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def _get_query_type(statement: str) -> str:
    """Extract query type from SQL statement."""
    if not statement:
        return "unknown"
    statement_upper = statement.strip().upper()
    if statement_upper.startswith("SELECT"):
        return "select"
    elif statement_upper.startswith("INSERT"):
        return "insert"
    elif statement_upper.startswith("UPDATE"):
        return "update"
    elif statement_upper.startswith("DELETE"):
        return "delete"
    return "other"


# Query timing event listeners (attached to sync engine for cursor events)
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Record query start time before execution."""
    _query_start_time.set(time.perf_counter())


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Record query duration and log slow queries."""
    start_time = _query_start_time.get()
    if start_time:
        duration = time.perf_counter() - start_time
        query_type = _get_query_type(statement)

        # Record duration in Prometheus histogram
        DB_QUERY_DURATION.labels(query_type=query_type).observe(duration)

        # Log and count slow queries
        if duration > SLOW_QUERY_THRESHOLD:
            DB_SLOW_QUERIES.labels(query_type=query_type).inc()
            logger.warning(
                "slow_query_detected",
                query_type=query_type,
                duration_ms=round(duration * 1000, 2),
                statement=statement[:200] if statement else None,
            )


# Connection pool monitoring
@event.listens_for(engine.sync_engine, "checkout")
def _on_checkout(dbapi_conn, connection_record, connection_proxy):
    """Track connection checkout from pool."""
    pool = engine.sync_engine.pool
    DB_CONNECTION_POOL_SIZE.set(pool.size())
    DB_CONNECTION_POOL_CHECKED_OUT.set(pool.checkedout())


@event.listens_for(engine.sync_engine, "checkin")
def _on_checkin(dbapi_conn, connection_record):
    """Track connection checkin to pool."""
    pool = engine.sync_engine.pool
    DB_CONNECTION_POOL_SIZE.set(pool.size())
    DB_CONNECTION_POOL_CHECKED_OUT.set(pool.checkedout())
