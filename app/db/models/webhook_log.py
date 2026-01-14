"""Webhook audit log model."""

from datetime import datetime

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class WebhookLog(Base, UUIDMixin):
    """Audit log for all incoming webhooks."""

    __tablename__ = "webhook_logs"

    # Request info
    source: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    headers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Processing
    processed: Mapped[bool] = mapped_column(default=False, nullable=False)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Response
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Timestamps
    received_at: Mapped[datetime] = mapped_column(index=True, nullable=False)

    __table_args__ = (
        Index("ix_webhook_logs_recent", "received_at", postgresql_using="btree"),
    )
