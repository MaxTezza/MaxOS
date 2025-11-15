"""Logging helper that honors settings and supports JSON output."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from max_os.utils.config import Settings


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - trivial
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(settings: Settings) -> None:
    config = settings.logging or {}
    level_name = str(config.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    json_mode = bool(config.get("json", False))
    log_file = config.get("file")

    if logging.getLogger().handlers:
        return

    handlers = []
    stream_handler = logging.StreamHandler()
    handlers.append(stream_handler)

    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_path))
        except OSError:
            # Fall back to stdout-only logging when the path is not writable
            pass

    formatter: logging.Formatter = JSONFormatter() if json_mode else logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(level=level, handlers=handlers)
