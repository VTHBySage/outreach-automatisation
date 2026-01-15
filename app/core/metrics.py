"""Prometheus metrics for application monitoring."""

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

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

# Email engagement metrics
EMAIL_OPENS = Counter(
    "email_opens_total",
    "Total email opens tracked",
    ["campaign_id"],
)
EMAIL_CLICKS = Counter(
    "email_clicks_total",
    "Total email link clicks tracked",
    ["campaign_id"],
)
EMAIL_REPLIES = Counter(
    "email_replies_total",
    "Total email replies received",
    ["campaign_id"],
)
EMAIL_BOUNCES = Counter(
    "email_bounces_total",
    "Total email bounces",
    ["campaign_id", "bounce_type"],  # hard, soft
)
EMAIL_UNSUBSCRIBES = Counter(
    "email_unsubscribes_total",
    "Total email unsubscribes",
    ["campaign_id"],
)

# Rate limit monitoring metrics
RATE_LIMIT_HITS = Counter(
    "rate_limit_hits_total",
    "Total times rate limit was hit (429 responses)",
    ["integration"],  # hubspot, smartlead, apollo, connectsafely
)
RATE_LIMIT_RETRIES = Counter(
    "rate_limit_retries_total",
    "Total rate limit retry attempts",
    ["integration"],
)
API_REQUESTS_MINUTE = Gauge(
    "api_requests_per_minute",
    "Current API requests per minute by integration",
    ["integration"],
)
RATE_LIMIT_THRESHOLD_ALERTS = Counter(
    "rate_limit_threshold_alerts_total",
    "Times rate limit threshold (80%) was crossed",
    ["integration"],
)

# Database performance metrics
DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query execution time",
    ["query_type"],  # select, insert, update, delete
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)
DB_SLOW_QUERIES = Counter(
    "db_slow_queries_total",
    "Total slow queries (>100ms)",
    ["query_type"],
)
DB_CONNECTION_POOL_SIZE = Gauge(
    "db_connection_pool_size",
    "Current database connection pool size",
)
DB_CONNECTION_POOL_CHECKED_OUT = Gauge(
    "db_connection_pool_checked_out",
    "Number of connections currently checked out from pool",
)

# ROI and Business Metrics
EMAILS_SENT = Counter(
    "emails_sent_total",
    "Total emails sent by campaign",
    ["campaign_id"],
)
MEETINGS_BOOKED = Counter(
    "meetings_booked_total",
    "Total meetings booked by campaign",
    ["campaign_id"],
)
INTERESTED_LEADS = Counter(
    "interested_leads_total",
    "Total leads categorized as interested by campaign",
    ["campaign_id"],
)
CAMPAIGN_COST = Gauge(
    "campaign_cost_dollars",
    "Total campaign cost in dollars",
    ["campaign_id"],
)
CAMPAIGN_POTENTIAL_REVENUE = Gauge(
    "campaign_potential_revenue_dollars",
    "Potential revenue from meetings booked",
    ["campaign_id"],
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
    "EMAIL_OPENS",
    "EMAIL_CLICKS",
    "EMAIL_REPLIES",
    "EMAIL_BOUNCES",
    "EMAIL_UNSUBSCRIBES",
    "RATE_LIMIT_HITS",
    "RATE_LIMIT_RETRIES",
    "API_REQUESTS_MINUTE",
    "RATE_LIMIT_THRESHOLD_ALERTS",
    "DB_QUERY_DURATION",
    "DB_SLOW_QUERIES",
    "DB_CONNECTION_POOL_SIZE",
    "DB_CONNECTION_POOL_CHECKED_OUT",
    "EMAILS_SENT",
    "MEETINGS_BOOKED",
    "INTERESTED_LEADS",
    "CAMPAIGN_COST",
    "CAMPAIGN_POTENTIAL_REVENUE",
]
