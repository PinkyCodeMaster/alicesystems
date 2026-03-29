import { Platform } from 'react-native';

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user_id: string;
  display_name: string;
};

export type User = {
  id: string;
  site_id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: number;
};

export type RootResponse = {
  service: string;
  version: string;
  site_id: string;
  site_name: string;
  setup_completed: boolean;
  requires_onboarding: boolean;
};

export type HubSetupStatus = {
  setup_completed: boolean;
  requires_onboarding: boolean;
  site_id: string;
  site_name: string;
  timezone: string;
  owner_count: number;
  completed_at: string | null;
  source: string;
};

export type HubSetupResponse = {
  access_token: string;
  token_type: string;
  user_id: string;
  display_name: string;
  setup_completed: boolean;
  site_id: string;
  site_name: string;
  timezone: string;
  rooms: Array<{
    id: string;
    name: string;
    slug: string;
  }>;
};

export type Room = {
  id: string;
  site_id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
};

export type Device = {
  id: string;
  site_id: string;
  room_id: string | null;
  room_name?: string | null;
  name: string;
  model: string;
  device_type: string;
  protocol: string;
  status: string;
  provisioning_status: string;
  fw_version: string | null;
  mqtt_client_id: string;
  last_seen_at: string | null;
};

export type Entity = {
  id: string;
  site_id: string;
  room_id: string | null;
  device_id: string;
  capability_id: string;
  kind: string;
  name: string;
  slug: string;
  writable: number;
  traits_json: string;
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
  site_id: string;
  actor_type: string;
  actor_id: string | null;
  action: string;
  target_type: string;
  target_id: string | null;
  severity: string;
  metadata_json: string;
  created_at: string;
};

export type DeviceDetailEntity = {
  id: string;
  room_id: string | null;
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
  entities: DeviceDetailEntity[];
  audit_events: AuditEvent[];
};

export type StackHealth = {
  api_status: string;
  api_service: string;
  environment: string;
  broker: {
    enabled: boolean;
    host: string;
    port: number;
    started: boolean;
    connected: boolean;
  };
  devices: {
    total: number;
    online: number;
    offline: number;
    timeout_seconds: number;
  };
  latest_command_request: StackHealthCommandEvent | null;
  latest_command_ack: StackHealthCommandEvent | null;
};

export type StackHealthCommandEvent = {
  action: string;
  target_id: string | null;
  actor_id: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type ProvisioningSessionResponse = {
  session_id: string;
  bootstrap_id: string;
  status: string;
  claim_token: string;
  expires_at: string;
  requested_device_name: string | null;
  room_id: string | null;
};

export type ProvisioningSessionStatusResponse = {
  session_id: string;
  bootstrap_id: string;
  status: string;
  expires_at: string;
  requested_device_name: string | null;
  room_id: string | null;
  claimed_device_id: string | null;
  completed_at: string | null;
};

export type LocalDeviceProvisioningResponse = {
  accepted?: boolean;
  restart_scheduled?: boolean;
  bootstrap_id?: string;
  setup_ap_ssid?: string;
  detail?: string;
};

export type DeviceDeleteResponse = {
  device_id: string;
  removed: boolean;
};

export type DeviceUpdateRequest = {
  name: string;
  room_id: string | null;
};

export type DeviceBootstrapRecordResponse = {
  id: string;
  model: string;
  device_type: string;
  hardware_revision: string | null;
  default_device_id: string | null;
  status: string;
  claimed_device_id: string | null;
  metadata_json: string;
  created_at: string;
  updated_at: string;
  claimed_at: string | null;
};

const DEFAULT_API_PORT = 8000;

export function resolveDefaultApiBaseUrl(): string {
  const configured = process.env.EXPO_PUBLIC_ALICE_API_BASE_URL?.trim();
  if (configured) {
    return normalizeApiBaseUrl(configured);
  }

  if (Platform.OS === 'android') {
    return `http://10.0.2.2:${DEFAULT_API_PORT}/api/v1`;
  }

   if (Platform.OS === 'web') {
    return `http://127.0.0.1:${DEFAULT_API_PORT}/api/v1`;
  }

  return `http://alice.local:${DEFAULT_API_PORT}/api/v1`;
}

export function normalizeApiBaseUrl(value: string): string {
  let normalized = value.trim();
  if (!normalized) {
    return resolveDefaultApiBaseUrl();
  }

  if (!/^[a-z]+:\/\//i.test(normalized)) {
    normalized = `http://${normalized}`;
  }

  normalized = normalized.replace(/\/+$/, '');
  if (!normalized.endsWith('/api/v1')) {
    normalized = `${normalized}/api/v1`;
  }

  return normalized;
}

export function buildDashboardWebSocketUrl(apiBaseUrl: string): string {
  const origin = apiBaseUrl.replace(/\/api\/v1$/, '');
  return `${origin.replace(/^http/, 'ws')}/api/v1/ws/dashboard`;
}

export function authenticateDashboardWebSocket(websocket: WebSocket, token: string): void {
  websocket.send(
    JSON.stringify({
      type: 'authenticate',
      token,
    }),
  );
}

export async function apiRequest<T>(
  apiBaseUrl: string,
  path: string,
  init?: RequestInit,
  token?: string | null,
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set('Accept', 'application/json');

  if (init?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const contentType = response.headers.get('Content-Type') ?? '';

    if (contentType.includes('application/json')) {
      try {
        const payload = (await response.json()) as { detail?: string };
        throw new Error(payload.detail || `${response.status} ${response.statusText}`);
      } catch (error) {
        if (error instanceof Error) {
          throw error;
        }
      }
    }

    const detail = await response.text();
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export async function loginRequest(
  apiBaseUrl: string,
  email: string,
  password: string,
): Promise<LoginResponse> {
  return apiRequest<LoginResponse>(
    apiBaseUrl,
    '/auth/login',
    {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    },
  );
}

export async function completeHubSetupRequest(
  apiBaseUrl: string,
  args: {
    siteName: string;
    timezone: string;
    ownerEmail: string;
    ownerDisplayName: string;
    password: string;
    roomNames: string[];
  },
): Promise<HubSetupResponse> {
  return apiRequest<HubSetupResponse>(apiBaseUrl, '/system/setup', {
    method: 'POST',
    body: JSON.stringify({
      site_name: args.siteName,
      timezone: args.timezone,
      owner_email: args.ownerEmail,
      owner_display_name: args.ownerDisplayName,
      password: args.password,
      room_names: args.roomNames,
    }),
  });
}

export async function sendSwitchCommand(
  apiBaseUrl: string,
  token: string,
  entityId: string,
  on: boolean,
): Promise<void> {
  await apiRequest(
    apiBaseUrl,
    `/entities/${entityId}/commands`,
    {
      method: 'POST',
      body: JSON.stringify({
        command: 'switch.set',
        params: { on },
      }),
    },
    token,
  );
}

export async function createProvisioningSession(
  apiBaseUrl: string,
  token: string,
  args: {
    bootstrapId: string;
    setupCode: string;
    requestedDeviceName?: string;
    roomId?: string | null;
  },
): Promise<ProvisioningSessionResponse> {
  return apiRequest<ProvisioningSessionResponse>(
    apiBaseUrl,
    '/provisioning/sessions',
    {
      method: 'POST',
      body: JSON.stringify({
        bootstrap_id: args.bootstrapId,
        setup_code: args.setupCode,
        requested_device_name: args.requestedDeviceName?.trim() || null,
        room_id: args.roomId ?? null,
      }),
    },
    token,
  );
}

export async function createBootstrapRecord(
  apiBaseUrl: string,
  token: string,
  args: {
    bootstrapId: string;
    setupCode: string;
    model: string;
    deviceType: string;
    hardwareRevision?: string | null;
    defaultDeviceId?: string | null;
    metadata?: Record<string, unknown>;
  },
): Promise<DeviceBootstrapRecordResponse> {
  return apiRequest<DeviceBootstrapRecordResponse>(
    apiBaseUrl,
    '/provisioning/bootstrap-records',
    {
      method: 'POST',
      body: JSON.stringify({
        bootstrap_id: args.bootstrapId,
        setup_code: args.setupCode,
        model: args.model,
        device_type: args.deviceType,
        hardware_revision: args.hardwareRevision ?? null,
        default_device_id: args.defaultDeviceId ?? null,
        metadata: args.metadata ?? {},
      }),
    },
    token,
  );
}

export async function createRoomRequest(
  apiBaseUrl: string,
  token: string,
  name: string,
): Promise<Room> {
  return apiRequest<Room>(
    apiBaseUrl,
    '/rooms',
    {
      method: 'POST',
      body: JSON.stringify({ name }),
    },
    token,
  );
}

export async function getProvisioningSessionStatus(
  apiBaseUrl: string,
  token: string,
  sessionId: string,
): Promise<ProvisioningSessionStatusResponse> {
  return apiRequest<ProvisioningSessionStatusResponse>(
    apiBaseUrl,
    `/provisioning/sessions/${sessionId}`,
    undefined,
    token,
  );
}

export async function deleteDeviceRequest(
  apiBaseUrl: string,
  token: string,
  deviceId: string,
): Promise<DeviceDeleteResponse> {
  return apiRequest<DeviceDeleteResponse>(
    apiBaseUrl,
    `/devices/${deviceId}`,
    {
      method: 'DELETE',
    },
    token,
  );
}

export async function updateDeviceRequest(
  apiBaseUrl: string,
  token: string,
  deviceId: string,
  payload: DeviceUpdateRequest,
): Promise<Device> {
  return apiRequest<Device>(
    apiBaseUrl,
    `/devices/${deviceId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function normalizeDeviceSetupBaseUrl(value: string): string {
  let normalized = value.trim();
  if (!normalized) {
    normalized = 'http://192.168.4.1';
  }
  if (!/^[a-z]+:\/\//i.test(normalized)) {
    normalized = `http://${normalized}`;
  }
  return normalized.replace(/\/+$/, '');
}

export async function sendLocalDeviceProvisioning(
  deviceBaseUrl: string,
  args: {
    bootstrapId: string;
    claimToken: string;
    wifiSsid?: string;
    wifiPassword?: string;
    hubApiBaseUrl?: string;
  },
): Promise<LocalDeviceProvisioningResponse> {
  const response = await fetch(`${normalizeDeviceSetupBaseUrl(deviceBaseUrl)}/provision`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      bootstrap_id: args.bootstrapId,
      claim_token: args.claimToken,
      wifi_ssid: args.wifiSsid?.trim() || undefined,
      wifi_password: args.wifiPassword ?? undefined,
      hub_api_base_url: args.hubApiBaseUrl?.trim() || undefined,
    }),
  });

  const contentType = response.headers.get('Content-Type') ?? '';
  let payload: LocalDeviceProvisioningResponse | null = null;
  if (contentType.includes('application/json')) {
    payload = (await response.json()) as LocalDeviceProvisioningResponse;
  }

  if (!response.ok) {
    throw new Error(payload?.detail || `${response.status} ${response.statusText}`);
  }

  return payload ?? {};
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return 'Never';
  }

  return new Date(value).toLocaleString();
}

export function formatStateValue(value: Record<string, unknown> | null | undefined): string {
  if (!value || Object.keys(value).length === 0) {
    return 'No state yet';
  }

  return Object.entries(value)
    .map(([key, entry]) => `${key}: ${String(entry)}`)
    .join(' | ');
}

export function parseMetadata(value: string): Record<string, unknown> {
  try {
    return JSON.parse(value);
  } catch {
    return {};
  }
}

export function isUnauthorizedError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false;
  }

  return error.message.includes('401') || error.message.includes('Missing bearer') || error.message.includes('Invalid token');
}
