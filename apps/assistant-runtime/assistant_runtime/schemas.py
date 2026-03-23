from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ToolTrace(BaseModel):
    tool: str
    status: str
    detail: str


class ChatResponse(BaseModel):
    mode: str
    success: bool
    reply: str
    tool_traces: list[ToolTrace]


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
