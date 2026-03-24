from __future__ import annotations

import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx

from assistant_runtime.clients.home_os_gateway import HomeOsGateway
from assistant_runtime.core.config import Settings
from assistant_runtime.schemas import ChatRequest, ChatResponse, ChatStreamError, HealthResponse, SessionMessageResponse, SessionMessagesResponse
from assistant_runtime.services.assistant_service import AssistantService
from assistant_runtime.services.session_store import SessionStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    gateway = HomeOsGateway(settings)
    store = SessionStore(settings.session_store_path)
    service = AssistantService(gateway=gateway, settings=settings, store=store)

    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get(f"{settings.api_v1_prefix}/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        dependencies = await service.health_dependencies()
        return HealthResponse(
            status="ok",
            service=settings.app_name,
            environment=settings.environment,
            dependencies=dependencies,
        )

    @app.post(f"{settings.api_v1_prefix}/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest) -> ChatResponse:
        try:
            return await service.chat(message=payload.message, session_id=payload.session_id)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Home OS is unreachable at {settings.home_os_base_url}. "
                    "Start hub-api first, then retry."
                ),
            ) from exc
        except Exception as exc:  # pragma: no cover - surfaced to caller cleanly
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post(f"{settings.api_v1_prefix}/chat/stream")
    async def chat_stream(payload: ChatRequest) -> StreamingResponse:
        async def event_stream():
            try:
                async for event in service.chat_stream(
                    message=payload.message,
                    session_id=payload.session_id,
                ):
                    yield _format_sse_event(event["event"], event["data"])
            except httpx.HTTPError as exc:
                detail = (
                    f"Home OS is unreachable at {settings.home_os_base_url}. "
                    "Start hub-api first, then retry."
                )
                yield _format_sse_event("error", ChatStreamError(detail=detail).model_dump())
            except Exception as exc:  # pragma: no cover - surfaced to caller cleanly
                yield _format_sse_event("error", ChatStreamError(detail=str(exc)).model_dump())

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get(f"{settings.api_v1_prefix}/sessions/{{session_id}}/messages", response_model=SessionMessagesResponse)
    async def list_session_messages(session_id: str) -> SessionMessagesResponse:
        try:
            messages = await service.list_messages(session_id=session_id)
        except Exception as exc:  # pragma: no cover - surfaced to caller cleanly
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return SessionMessagesResponse(
            items=[
                SessionMessageResponse(
                    id=item.id,
                    session_id=item.session_id,
                    role=item.role,
                    content=item.content,
                    created_at=item.created_at,
                    mode=item.mode,
                    success=item.success,
                    metadata=item.metadata,
                )
                for item in messages
            ]
        )

    return app


def _format_sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


app = create_app()
