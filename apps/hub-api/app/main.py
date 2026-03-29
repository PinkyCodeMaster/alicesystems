import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
import logging
from time import perf_counter
from uuid import uuid4

from app.api.router import api_router
from app.core.config import Settings, get_settings, set_settings_override
from app.core.db import close_engine, init_db
from app.core.db import get_session_factory
from app.core.events import event_bus
from app.core.logging import close_logging, configure_logging
from app.core.mqtt import start_mqtt, stop_mqtt
from app.services.auth_service import AuthService
from app.services.bootstrap_service import bootstrap_defaults
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)
_SENSITIVE_KEYS = {"password", "token", "access_token", "refresh_token", "authorization", "secret", "api_key"}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    init_db()
    bootstrap_defaults()
    logger.info("Alice Home OS startup complete", extra={"event": {"action": "app.startup"}})
    start_mqtt(settings)
    try:
        yield
    finally:
        logger.info("Alice Home OS shutdown starting", extra={"event": {"action": "app.shutdown"}})
        stop_mqtt()
        close_engine()
        close_logging()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    close_engine()
    close_logging()
    set_settings_override(settings)
    configure_logging(settings)

    app = FastAPI(
        title="Alice Home OS API",
        version="0.1.0",
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _redact_value(value):
        if isinstance(value, dict):
            return {
                key: ("***REDACTED***" if key.lower() in _SENSITIVE_KEYS else _redact_value(item))
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [_redact_value(item) for item in value]
        return value

    async def _read_request_body(request: Request) -> dict | str | None:
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None
        if not settings.log_http_request_bodies:
            return None

        body = await request.body()
        if not body:
            return None

        truncated = body[: settings.log_http_request_body_max_bytes]

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive  # type: ignore[attr-defined]

        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                return _redact_value(json.loads(truncated.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return "<invalid-json>"

        try:
            return truncated.decode("utf-8")
        except UnicodeDecodeError:
            return "<binary-body>"

    @app.middleware("http")
    async def log_http_requests(request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:16]}"
        request.state.request_id = request_id
        request_body = await _read_request_body(request)
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started) * 1000, 2)
            logger.exception(
                "HTTP request failed",
                extra={
                    "event": {
                        "action": "http.request_failed",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "query": request.url.query,
                        "duration_ms": duration_ms,
                        "client": request.client.host if request.client else None,
                        "body": request_body,
                    }
                },
            )
            raise

        duration_ms = round((perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        if (
            not settings.log_http_include_docs_requests
            and request.url.path in {"/openapi.json", "/docs", "/redoc"}
        ):
            return response
        event = {
            "action": "http.request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client": request.client.host if request.client else None,
        }
        if request_body is not None:
            event["body"] = request_body
        logger.info(
            "HTTP request handled",
            extra={"event": event},
        )
        return response

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.websocket(f"{settings.api_v1_prefix}/ws/dashboard")
    async def dashboard_events(websocket: WebSocket) -> None:
        await websocket.accept()

        try:
            auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=5)
        except TimeoutError:
            await websocket.close(code=4401, reason="Dashboard authentication timed out")
            return
        except Exception:
            await websocket.close(code=4401, reason="Invalid dashboard authentication payload")
            return

        if auth_message.get("type") != "authenticate" or not isinstance(auth_message.get("token"), str):
            await websocket.close(code=4401, reason="Missing dashboard token")
            return

        token = auth_message["token"].strip()
        if not token:
            await websocket.close(code=4401, reason="Missing dashboard token")
            return

        session = get_session_factory()()
        try:
            user = AuthService(session).get_user_from_token(token)
        finally:
            session.close()

        if user is None:
            await websocket.close(code=4401, reason="Invalid token")
            return

        await websocket.send_json({"type": "connected", "user_id": user.id})
        queue = event_bus.connect()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20)
                    await websocket.send_json(event)
                except TimeoutError:
                    await websocket.send_json({"type": "ping"})
        except WebSocketDisconnect:
            return
        finally:
            event_bus.disconnect(queue)

    return app


app = create_app()
