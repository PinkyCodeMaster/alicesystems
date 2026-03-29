export type AliceDeviceQrPayload = {
  version: number;
  bootstrapId: string;
  setupCode: string;
  model?: string;
  deviceType?: string;
  setupApSsid?: string;
};

function normalizeString(value: unknown): string | undefined {
  if (typeof value !== 'string') {
    return undefined;
  }

  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function validatePayload(payload: Partial<AliceDeviceQrPayload>): AliceDeviceQrPayload {
  const bootstrapId = normalizeString(payload.bootstrapId);
  const setupCode = normalizeString(payload.setupCode);
  const version = typeof payload.version === 'number' ? payload.version : 1;

  if (!bootstrapId) {
    throw new Error('QR payload is missing bootstrap_id.');
  }

  if (!setupCode) {
    throw new Error('QR payload is missing setup_code.');
  }

  return {
    version,
    bootstrapId,
    setupCode,
    model: normalizeString(payload.model),
    deviceType: normalizeString(payload.deviceType),
    setupApSsid: normalizeString(payload.setupApSsid),
  };
}

function parseJsonPayload(raw: string): AliceDeviceQrPayload {
  const parsed = JSON.parse(raw) as Record<string, unknown>;
  return validatePayload({
    version: typeof parsed.v === 'number' ? parsed.v : 1,
    bootstrapId: normalizeString(parsed.bootstrap_id),
    setupCode: normalizeString(parsed.setup_code),
    model: normalizeString(parsed.model),
    deviceType: normalizeString(parsed.device_type),
    setupApSsid: normalizeString(parsed.setup_ap_ssid),
  });
}

function parseUriPayload(raw: string): AliceDeviceQrPayload {
  const url = new URL(raw);
  const query = url.searchParams;

  return validatePayload({
    version: Number(query.get('v') || '1'),
    bootstrapId: query.get('bootstrap_id') ?? undefined,
    setupCode: query.get('setup_code') ?? undefined,
    model: query.get('model') ?? undefined,
    deviceType: query.get('device_type') ?? undefined,
    setupApSsid: query.get('setup_ap_ssid') ?? undefined,
  });
}

export function parseAliceDeviceQrPayload(raw: string): AliceDeviceQrPayload {
  const trimmed = raw.trim();
  if (!trimmed) {
    throw new Error('QR payload is empty.');
  }

  if (trimmed.startsWith('{')) {
    return parseJsonPayload(trimmed);
  }

  if (trimmed.startsWith('alice://')) {
    return parseUriPayload(trimmed);
  }

  throw new Error('Unsupported QR payload format.');
}
