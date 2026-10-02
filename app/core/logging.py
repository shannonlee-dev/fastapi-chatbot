"""Application 운영 event를 JSON line 파일에 제한된 크기로 저장한다."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

current_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestContextFilter(logging.Filter):
    """기록 시점에 현재 request ID를 log record에 연결한다."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id.get() or getattr(
            record, "request_id", None
        )
        return True


class JsonLogFormatter(logging.Formatter):
    """예외 원문과 stack을 제외한 운영 event만 직렬화한다."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "request_id": getattr(record, "request_id", None),
                "event": record.getMessage(),
            },
            ensure_ascii=False,
        )


def configure_logging(*, log_level: str, log_file: Path) -> None:
    """Console과 application 파일 log를 구성하고 중복 handler를 방지한다."""

    level = getattr(logging, log_level)
    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level)
    logger = logging.getLogger("app")
    logger.setLevel(level)
    log_file = log_file.expanduser().resolve()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    for handler in list(logger.handlers):
        if isinstance(handler, RotatingFileHandler):
            logger.removeHandler(handler)
            handler.close()
    handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
