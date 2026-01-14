"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False  # Secure default: disabled
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: SecretStr  # Required - no default

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]  # Frontend origin(s)
    cors_allow_credentials: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/outreach"
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_recycle: int = 3600  # Recycle connections after 1 hour

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # SmartLead
    smartlead_api_key: SecretStr = SecretStr("")
    smartlead_webhook_secret: SecretStr = SecretStr("")

    # HubSpot
    hubspot_access_token: SecretStr = SecretStr("")
    hubspot_api_base_url: str = "https://api.hubapi.com"
    hubspot_owner_id: str = ""  # Default HubSpot owner for task assignment
    hubspot_portal_id: str = ""  # HubSpot portal ID for generating URLs

    # Apollo
    apollo_api_key: SecretStr = SecretStr("")

    # ConnectSafely
    connectsafely_api_key: SecretStr = SecretStr("")
    connectsafely_webhook_secret: SecretStr = SecretStr("")

    # MS Teams
    msteams_webhook_url: str = ""

    # OpenAI
    # Note: Using gpt-4o which supports structured JSON output (json_schema response_format)
    # See: https://platform.openai.com/docs/guides/structured-outputs
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 1000

    # Monitoring
    sentry_dsn: str = ""
    sentry_environment: str = ""  # Auto-detected from app_env if not set
    sentry_traces_sample_rate: float = 0.1  # 10% for performance monitoring
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    # Scheduler
    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"

    # Rate limiting
    rate_limit_per_minute: int = 100
    webhook_rate_limit_per_minute: int = 1000

    @field_validator("app_debug", mode="before")
    @classmethod
    def validate_debug(cls, v, info):
        """Disable debug mode in production unless explicitly enabled."""
        # info.data may not have app_env yet during validation order
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate critical settings for production environment."""
        if self.app_env == "production":
            # Enforce debug disabled in production
            if self.app_debug:
                raise ValueError("app_debug must be False in production")

            # Validate secret key is set and secure
            secret = self.app_secret_key.get_secret_value()
            if not secret or len(secret) < 32:
                raise ValueError("app_secret_key must be at least 32 characters in production")
            if secret == "change-me-in-production":
                raise ValueError("app_secret_key must be changed from default in production")

            # Validate database URL is not default
            if "localhost" in self.database_url and "postgres:postgres" in self.database_url:
                raise ValueError("database_url should not use default credentials in production")

            # Require OpenAI key for AI features
            if not self.openai_api_key.get_secret_value():
                raise ValueError("openai_api_key is required in production")

            # Require HubSpot for CRM sync
            if not self.hubspot_access_token.get_secret_value():
                raise ValueError("hubspot_access_token is required in production")

            # Restrict CORS origins in production
            if "*" in self.cors_origins:
                raise ValueError("CORS origins cannot be '*' in production")

        return self

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
