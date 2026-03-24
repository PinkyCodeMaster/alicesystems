"use client";

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user_id: string;
  display_name: string;
};

export type User = {
  id: string;
  email: string;
  display_name: string;
  role: string;
};

export type Device = {
  id: string;
  name: string;
  model: string;
  device_type: string;
  status: string;
  fw_version: string | null;
  last_seen_at: string | null;
};

export type Entity = {
  id: string;
  device_id: string;
  capability_id: string;
  kind: string;
  name: string;
  writable: number;
};

export type EntityState = {
  entity_id: string;
  value: Record<string, unknown>;
  source: string;
  updated_at: string;
  version: number;
};

export type AuditEvent = {
  id: string;
  actor_id: string | null;
  action: string;
  target_id: string | null;
  severity: string;
  metadata_json: string;
  created_at: string;
};

export type AutoLightSettings = {
  enabled: boolean;
  sensor_entity_id: string | null;
  target_entity_id: string | null;
  mode: string;
  on_lux: number;
  off_lux: number;
  on_raw: number;
  off_raw: number;
  block_on_during_daytime: boolean;
  daytime_start_hour: number;
  daytime_end_hour: number;
  source: string;
  updated_at: string | null;
};

export type StackHealthBroker = {
  enabled: boolean;
  host: string;
  port: number;
  started: boolean;
  connected: boolean;
};

export type StackHealthDevices = {
  total: number;
  online: number;
  offline: number;
  timeout_seconds: number;
};

export type StackHealthCommandEvent = {
  action: string;
  target_id: string | null;
  actor_id: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type StackHealth = {
  api_status: string;
  api_service: string;
  environment: string;
  broker: StackHealthBroker;
  devices: StackHealthDevices;
  latest_command_request: StackHealthCommandEvent | null;
  latest_command_ack: StackHealthCommandEvent | null;
};

export type HealthResponse = {
  status: string;
  service: string;
  environment: string;
};

export type HealthCheckState = {
  status: "checking" | "reachable" | "unreachable";
  message: string;
};

export type DeviceEntity = {
  id: string;
  capability_id: string;
  kind: string;
  name: string;
  writable: number;
  traits_json: string;
  state: Record<string, unknown> | null;
  state_source: string | null;
  state_updated_at: string | null;
  state_version: number | null;
};

export type DeviceDetail = {
  device: Device;
  entities: DeviceEntity[];
  audit_events: AuditEvent[];
};

export type AssistantDependencyStatus = {
  reachable: boolean;
  detail: string;
};

export type AssistantHealthResponse = {
  status: string;
  service: string;
  environment: string;
  dependencies: Record<string, AssistantDependencyStatus>;
};

export type AssistantToolTrace = {
  tool: string;
  status: string;
  detail: string;
};

export type AssistantDebug = {
  configured_mode: string;
  response_mode: string;
  planner_source: string;
  fallback_used: boolean;
  ollama_configured: boolean;
  ollama_model: string | null;
  planner_error: string | null;
  home_os_base_url: string;
};

export type AssistantChatResponse = {
  session_id: string;
  mode: string;
  success: boolean;
  reply: string;
  tool_traces: AssistantToolTrace[];
  debug: AssistantDebug;
};

export type AssistantSessionMessage = {
  id: number;
  session_id: string;
  role: string;
  content: string;
  created_at: string;
  mode: string | null;
  success: boolean | null;
  metadata: Record<string, unknown>;
};

export type AssistantStreamStart = {
  session_id: string;
};

export type AssistantStreamDelta = {
  content: string;
};

export type AssistantStreamError = {
  detail: string;
};

export const TOKEN_KEY = "alice.dashboard.token";
const DEFAULT_API_PORT = 8000;
const DEFAULT_ASSISTANT_PORT = 8010;

export function resolveApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_ALICE_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/+$/, "");
  }

  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:${DEFAULT_API_PORT}/api/v1`;
  }

  return `http://localhost:${DEFAULT_API_PORT}/api/v1`;
}

export function resolveAssistantBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_ALICE_ASSISTANT_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/+$/, "");
  }

  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:${DEFAULT_ASSISTANT_PORT}/api/v1`;
  }

  return `http://localhost:${DEFAULT_ASSISTANT_PORT}/api/v1`;
}

export function parseMetadata(value: string): Record<string, unknown> {
  try {
    return JSON.parse(value);
  } catch {
    return {};
  }
}

export function formatState(value?: Record<string, unknown> | null): string {
  if (!value) return "No state";
  return Object.entries(value)
    .map(([key, entry]) => `${key}: ${String(entry)}`)
    .join(" | ");
}

export function formatDate(value?: string | null): string {
  if (!value) return "Never";
  return new Date(value).toLocaleString();
}

export function formatUserSubtitle(user?: User | null): string | undefined {
  if (!user) {
    return undefined;
  }

  return `${user.display_name} | ${user.email} | ${user.role}`;
}

export function formatCommandEventSummary(
  event: StackHealthCommandEvent | null,
): string {
  if (!event) return "No recent event";

  const command = String(event.metadata.command ?? "unknown");
  const status = event.metadata.status
    ? ` | ${String(event.metadata.status)}`
    : "";
  const target = event.target_id ? ` | ${event.target_id}` : "";
  return `${command}${status}${target}`;
}

export function buildDashboardWebSocketUrl(
  apiBaseUrl: string,
  token: string,
): string {
  const origin = apiBaseUrl.replace(/\/api\/v1$/, "");
  return `${origin.replace(/^http/, "ws")}/api/v1/ws/dashboard?token=${encodeURIComponent(token)}`;
}

export function getStatusVariant(status: string) {
  switch (status.toLowerCase()) {
    case "online":
      return "default";
    case "warning":
    case "degraded":
      return "secondary";
    default:
      return "outline";
  }
}

export async function apiFetch<T>(
  apiBaseUrl: string,
  path: string,
  token: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  headers.set("Authorization", `Bearer ${token}`);

  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export async function assistantFetch<T>(
  assistantBaseUrl: string,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");

  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${assistantBaseUrl}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export async function assistantStreamChat(
  assistantBaseUrl: string,
  payload: { message: string; session_id?: string | null },
  handlers: {
    onStart?: (value: AssistantStreamStart) => void;
    onTool?: (value: AssistantToolTrace) => void;
    onDelta?: (value: AssistantStreamDelta) => void;
    onDone?: (value: AssistantChatResponse) => void;
    onError?: (value: AssistantStreamError) => void;
  },
) {
  const response = await fetch(`${assistantBaseUrl}/chat/stream`, {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error("Assistant stream response did not include a body.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    let separatorIndex = buffer.indexOf("\n\n");
    while (separatorIndex !== -1) {
      const rawEvent = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);
      _dispatchAssistantStreamEvent(rawEvent, handlers);
      separatorIndex = buffer.indexOf("\n\n");
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    _dispatchAssistantStreamEvent(buffer, handlers);
  }
}

function _dispatchAssistantStreamEvent(
  rawEvent: string,
  handlers: {
    onStart?: (value: AssistantStreamStart) => void;
    onTool?: (value: AssistantToolTrace) => void;
    onDelta?: (value: AssistantStreamDelta) => void;
    onDone?: (value: AssistantChatResponse) => void;
    onError?: (value: AssistantStreamError) => void;
  },
) {
  const lines = rawEvent.split(/\r?\n/);
  let eventName = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (dataLines.length === 0) {
    return;
  }

  const payload = JSON.parse(dataLines.join("\n")) as
    | AssistantStreamStart
    | AssistantToolTrace
    | AssistantStreamDelta
    | AssistantChatResponse
    | AssistantStreamError;

  switch (eventName) {
    case "start":
      handlers.onStart?.(payload as AssistantStreamStart);
      break;
    case "tool":
      handlers.onTool?.(payload as AssistantToolTrace);
      break;
    case "delta":
      handlers.onDelta?.(payload as AssistantStreamDelta);
      break;
    case "done":
      handlers.onDone?.(payload as AssistantChatResponse);
      break;
    case "error":
      handlers.onError?.(payload as AssistantStreamError);
      break;
    default:
      break;
  }
}
