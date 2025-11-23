"""Logging helper that honors settings and supports JSON output."""
from __future__ import annotations

import logging
from pathlib import Path

import structlog
from structlog.dev import ConsoleRenderer
from structlog.processors import (
    JSONRenderer,
    StackInfoRenderer,
    TimeStamper,
    UnicodeDecoder,
    format_exc_info,
)

from max_os.utils.config import Settings


def configure_logging(settings: Settings) -> None:
    config = settings.logging or {}
    level_name = str(config.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    json_mode = bool(config.get("json", False))
    log_file = config.get("file")

    # Configure structlog processors
    shared_processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        StackInfoRenderer(),
        format_exc_info,
        UnicodeDecoder(),
    ]

    if json_mode:
        # For JSON output, add JSONRenderer
        processors = shared_processors + [JSONRenderer()]
    else:
        # For console output, add ConsoleRenderer
        processors = shared_processors + [ConsoleRenderer()]

    # Configure standard logging
    logging.basicConfig(level=level, handlers=[]) # Clear existing handlers
    
    # Add stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer() if not json_mode else structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    ))
    logging.getLogger().addHandler(stream_handler)

    # Add file handler if log_file is specified
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(), # Always JSON for file logs
                foreign_pre_chain=shared_processors,
            ))
            logging.getLogger().addHandler(file_handler)
        except OSError:
            # Fall back to stdout-only logging when the path is not writable
            pass

    # Configure structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Set specific logger levels for debugging

