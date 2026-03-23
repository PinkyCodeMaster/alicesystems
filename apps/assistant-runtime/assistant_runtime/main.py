from __future__ import annotations

from fastapi import FastAPI, HTTPException
import httpx

from assistant_runtime.clients.home_os_gateway import HomeOsGateway
from assistant_runtime.core.config import Settings
from assistant_runtime.schemas import ChatRequest, ChatResponse, HealthResponse
from assistant_runtime.services.assistant_service import AssistantService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    gateway = HomeOsGateway(settings)
    service = AssistantService(gateway)

    app = FastAPI(title=settings.app_name, version="0.1.0")

    @app.get(f"{settings.api_v1_prefix}/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=settings.app_name,
            environment=settings.environment,
        )

    @app.post(f"{settings.api_v1_prefix}/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest) -> ChatResponse:
        try:
            return await service.chat(payload.message)
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

    return app


app = create_app()
