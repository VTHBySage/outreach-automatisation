"""Prometheus metrics for application monitoring."""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# HTTP request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Webhook metrics
WEBHOOK_COUNT = Counter(
    "webhooks_total",
    "Total webhooks received",
    ["source"],
)
WEBHOOK_PROCESSING_TIME = Histogram(
    "webhook_processing_seconds",
    "Webhook processing time in seconds",
    ["source"],
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
)

# AI categorization metrics
CATEGORIZATION_COUNT = Counter(
    "categorizations_total",
    "Total AI categorizations",
    ["category", "subcategory"],
)
CATEGORIZATION_CONFIDENCE = Histogram(
    "categorization_confidence",
    "AI categorization confidence scores",
    buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99, 1.0],
)
CATEGORIZATION_LATENCY = Histogram(
    "categorization_duration_seconds",
    "AI categorization latency in seconds",
    buckets=[0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0],
)

# Task metrics
TASKS_CREATED = Counter(
    "tasks_created_total",
    "Total tasks created",
    ["priority", "category"],
)
TASKS_SYNCED = Counter(
    "tasks_synced_total",
    "Total tasks synced to HubSpot",
    ["status"],  # success, failed
)

# Lead suppression metrics
LEADS_SUPPRESSED = Counter(
    "leads_suppressed_total",
    "Total leads suppressed from campaigns",
    ["reason"],  # unsubscribe, hard_bounce
)


__all__ = [
    "generate_latest",
    "CONTENT_TYPE_LATEST",
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "WEBHOOK_COUNT",
    "WEBHOOK_PROCESSING_TIME",
    "CATEGORIZATION_COUNT",
    "CATEGORIZATION_CONFIDENCE",
    "CATEGORIZATION_LATENCY",
    "TASKS_CREATED",
    "TASKS_SYNCED",
    "LEADS_SUPPRESSED",
]
