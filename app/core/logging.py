"""Structured logging configuration."""

import gzip
import logging
import os
import shutil
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import structlog

from app.config import settings


class CompressedTimedRotatingFileHandler(TimedRotatingFileHandler):
    """TimedRotatingFileHandler that compresses rotated log files."""

    def __init__(self, *args, compress: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.compress = compress

    def doRollover(self):
        """Perform rollover and compress the rotated file."""
        super().doRollover()

        if self.compress:
            # Compress the most recently rotated file
            # The rotated file has a date suffix added by parent class
            for handler_file in Path(self.baseFilename).parent.glob(
                f"{Path(self.baseFilename).name}.*"
            ):
                if handler_file.suffix != ".gz" and handler_file.is_file():
                    self._compress_file(handler_file)

    def _compress_file(self, file_path: Path) -> None:
        """Compress a file using gzip."""
        gz_path = file_path.with_suffix(file_path.suffix + ".gz")
        try:
            with open(file_path, "rb") as f_in:
                with gzip.open(gz_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            file_path.unlink()  # Remove original after compression
        except Exception:
            pass  # Silently fail compression, keep original


def setup_logging() -> None:
    """Configure structured logging."""
    # Determine log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure structlog processors
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.log_format == "json":
        # JSON format for production
        shared_processors.append(structlog.processors.format_exc_info)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Console format for development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # JSON formatter for file logging (always JSON for parsing)
    json_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    # Stream handler (stdout) - always enabled for container environments
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(log_level)

    # File handler with rotation - optional, for non-container environments
    if settings.log_file_enabled:
        _setup_file_handler(root_logger, json_formatter, log_level)

    # Set levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def _setup_file_handler(
    logger: logging.Logger,
    formatter: logging.Formatter,
    level: int,
) -> None:
    """Set up rotating file handler for logging."""
    log_path = Path(settings.log_file_path)

    # Ensure log directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create rotating file handler
    file_handler = CompressedTimedRotatingFileHandler(
        filename=str(log_path),
        when="midnight",  # Rotate at midnight
        interval=settings.log_file_rotation_days,
        backupCount=settings.log_file_retention_days,
        compress=settings.log_file_compress,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    logger.addHandler(file_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)
