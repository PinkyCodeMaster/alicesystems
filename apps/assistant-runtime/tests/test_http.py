from __future__ import annotations

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
