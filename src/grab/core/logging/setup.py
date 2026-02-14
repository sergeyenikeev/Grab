from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from pythonjsonlogger import jsonlogger


class CorrelationIdFilter(logging.Filter):
    def __init__(self, correlation_id: str):
        super().__init__()
        self._correlation_id = correlation_id

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = self._correlation_id
        return True


def configure_logging(log_dir: Path, correlation_id: str, level: int = logging.INFO) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    utc_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    text_path = log_dir / f"grab-{utc_day}.log"
    json_path = log_dir / f"grab-{utc_day}.jsonl"

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    correlation_filter = CorrelationIdFilter(correlation_id)

    text_formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    json_formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(correlation_id)s %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(text_formatter)
    stream_handler.addFilter(correlation_filter)

    text_handler = logging.FileHandler(text_path, encoding="utf-8")
    text_handler.setFormatter(text_formatter)
    text_handler.addFilter(correlation_filter)

    json_handler = logging.FileHandler(json_path, encoding="utf-8")
    json_handler.setFormatter(json_formatter)
    json_handler.addFilter(correlation_filter)

    root.addHandler(stream_handler)
    root.addHandler(text_handler)
    root.addHandler(json_handler)


def get_logger(name: str, correlation_id: str) -> logging.LoggerAdapter:
    base_logger = logging.getLogger(name)
    return logging.LoggerAdapter(base_logger, extra={"correlation_id": correlation_id})
