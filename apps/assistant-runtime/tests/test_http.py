from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from assistant_runtime.core.config import Settings
from assistant_runtime.main import create_app


def test_chat_preflight_includes_cors_headers() -> None:
    app = create_app(
        Settings(
            cors_allow_origins="http://localhost:3000,http://192.168.0.29:3000",
        )
    )

    with TestClient(app) as client:
        response = client.options(
            "/api/v1/chat",
            headers={
                "Origin": "http://192.168.0.29:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://192.168.0.29:3000"


def test_chat_preflight_rejects_unknown_origin() -> None:
    app = create_app(Settings(cors_allow_origins="http://localhost:3000"))

    with TestClient(app) as client:
        response = client.options(
            "/api/v1/chat",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_chat_stream_returns_sse_events() -> None:
    app = create_app(Settings(cors_allow_origins="http://localhost:3000"))

    async def fake_stream(self, *, message: str, session_id: str | None = None):
        assert message == "hello"
        assert session_id is None
        yield {"event": "start", "data": {"session_id": "sess_test"}}
        yield {"event": "delta", "data": {"content": "Hi"}}
        yield {
            "event": "done",
            "data": {
                "session_id": "sess_test",
                "mode": "ollama",
                "success": True,
                "reply": "Hi",
                "tool_traces": [],
                "debug": {
                    "configured_mode": "auto",
                    "response_mode": "ollama",
                    "planner_source": "ollama",
                    "fallback_used": False,
                    "ollama_configured": True,
                    "ollama_model": "qwen3:4b",
                    "planner_error": None,
                    "home_os_base_url": "http://127.0.0.1:8000/api/v1",
                },
            },
        }

    with patch("assistant_runtime.main.AssistantService.chat_stream", fake_stream):
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat/stream",
                json={"message": "hello"},
            )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: start" in response.text
    assert "event: done" in response.text
