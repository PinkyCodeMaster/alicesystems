from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ToolTrace(BaseModel):
    tool: str
    status: str
    detail: str


class ChatDebug(BaseModel):
    configured_mode: str
    response_mode: str
    planner_source: str
    fallback_used: bool
    ollama_configured: bool
    ollama_model: str | None = None
    planner_error: str | None = None
    home_os_base_url: str


class ChatResponse(BaseModel):
    session_id: str
    mode: str
    success: bool
    reply: str
    tool_traces: list[ToolTrace]
    debug: ChatDebug


class ChatStreamStart(BaseModel):
    session_id: str


class ChatStreamDelta(BaseModel):
    content: str


class ChatStreamError(BaseModel):
    detail: str


class SessionMessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    created_at: str
    mode: str | None = None
    success: bool | None = None
    metadata: dict[str, Any]


class SessionMessagesResponse(BaseModel):
    items: list[SessionMessageResponse]


class DependencyStatus(BaseModel):
    reachable: bool
    detail: str


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    dependencies: dict[str, DependencyStatus]
