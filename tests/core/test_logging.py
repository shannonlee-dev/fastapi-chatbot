"""파일 log의 rotation과 request ID 연결·민감정보 제외를 검증한다."""

import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.request_id import RequestIdMiddleware


def test_runtime_log_is_saved_with_request_id_and_without_credentials(
    tmp_path: Path,
) -> None:
    from app.core.logging import configure_logging

    path = tmp_path / "logs" / "chatbot.log"
    configure_logging(log_level="INFO", log_file=path)
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_route() -> dict[str, str]:
        logging.getLogger("app.test").info("db_save_succeeded")
        return {"status": "ok"}

    with TestClient(app) as client:
        response = client.get(
            "/test?token=secret-query", headers={"cookie": "secret-cookie"}
        )
    entries = [json.loads(line) for line in path.read_text().splitlines()]
    events = {entry["event"].split()[0] for entry in entries}
    assert {
        "http_request_received",
        "http_request_completed",
        "db_save_succeeded",
    } <= events
    assert all(
        entry["request_id"] == response.headers["x-request-id"] for entry in entries
    )
    assert "secret-query" not in path.read_text()
    assert "secret-cookie" not in path.read_text()


def test_reconfiguring_log_does_not_duplicate_records(tmp_path: Path) -> None:
    from app.core.logging import configure_logging

    path = tmp_path / "chatbot.log"
    configure_logging(log_level="INFO", log_file=path)
    configure_logging(log_level="INFO", log_file=path)
    logging.getLogger("app.test").info("test_event")
    assert len(path.read_text().splitlines()) == 1
