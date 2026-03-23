"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Cpu, LogOut } from "lucide-react";

import { ModeToggle } from "@/components/mode-toggle";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

type Device = {
  id: string;
  name: string;
  model: string;
  device_type: string;
  status: string;
  fw_version: string | null;
  last_seen_at: string | null;
};

type DeviceEntity = {
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

type AuditEvent = {
  id: string;
  actor_id: string | null;
  action: string;
  target_id: string | null;
  severity: string;
  metadata_json: string;
  created_at: string;
};

type DeviceDetail = {
  device: Device;
  entities: DeviceEntity[];
  audit_events: AuditEvent[];
};

const TOKEN_KEY = "alice.dashboard.token";
const DEFAULT_API_PORT = 8000;

function resolveApiBaseUrl(): string {
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

function buildDashboardWebSocketUrl(apiBaseUrl: string, token: string): string {
  const origin = apiBaseUrl.replace(/\/api\/v1$/, "");
  return `${origin.replace(/^http/, "ws")}/api/v1/ws/dashboard?token=${encodeURIComponent(token)}`;
}

function formatDate(value?: string | null): string {
  if (!value) return "Never";
  return new Date(value).toLocaleString();
}

function formatState(value?: Record<string, unknown> | null): string {
  if (!value) return "No state";
  return Object.entries(value)
    .map(([key, entry]) => `${key}: ${String(entry)}`)
    .join(" | ");
}

function parseMetadata(value: string): Record<string, unknown> {
  try {
    return JSON.parse(value);
  } catch {
    return {};
  }
}

function getStatusVariant(status: string) {
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

async function apiFetch<T>(apiBaseUrl: string, path: string, token: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export default function DeviceDetailPage() {
  const params = useParams<{ deviceId: string }>();
  const deviceId = params.deviceId;
  const apiBaseUrl = useMemo(() => resolveApiBaseUrl(), []);
  const [token, setToken] = useState<string | null>(null);
  const [detail, setDetail] = useState<DeviceDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = window.localStorage.getItem(TOKEN_KEY);
    setToken(stored);
  }, []);

  const loadDetail = useCallback(async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const nextDetail = await apiFetch<DeviceDetail>(
        apiBaseUrl,
        `/devices/${deviceId}`,
        token,
      );
      setDetail(nextDetail);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to load device");
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, deviceId, token]);

  useEffect(() => {
    void loadDetail();
    if (!token) {
      return;
    }

    const interval = window.setInterval(() => void loadDetail(), 30000);
    return () => window.clearInterval(interval);
  }, [loadDetail, token]);

  useEffect(() => {
    if (!token) {
      return;
    }

    const websocket = new WebSocket(buildDashboardWebSocketUrl(apiBaseUrl, token));
    websocket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { target_id?: string; type?: string };
        if (
          payload.type &&
          payload.type !== "ping" &&
          payload.type !== "connected" &&
          (!payload.target_id || payload.target_id === deviceId || detail?.entities.some((entity) => entity.id === payload.target_id))
        ) {
          void loadDetail();
        }
      } catch {
        void loadDetail();
      }
    };

    return () => websocket.close();
  }, [apiBaseUrl, detail?.entities, deviceId, loadDetail, token]);

  const logout = () => {
    window.localStorage.removeItem(TOKEN_KEY);
    setToken(null);
  };

  if (!token) {
    return (
      <main className="min-h-screen bg-background">
        <div className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-4">
          <Card className="w-full rounded-3xl">
            <CardHeader>
              <CardTitle>Login required</CardTitle>
              <CardDescription>
                Return to the dashboard and sign in before opening device detail pages.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link className="inline-flex" href="/">
                <Button type="button">Back to dashboard</Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-6 md:px-6 lg:px-8">
        <header className="flex flex-col gap-4 rounded-3xl border bg-card p-6 shadow-sm md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <Link className="inline-flex" href="/">
              <Button size="sm" type="button" variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to dashboard
              </Button>
            </Link>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">
                {detail?.device.name ?? "Device detail"}
              </h1>
              <p className="text-sm text-muted-foreground">
                {detail?.device.id ?? deviceId}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <ModeToggle />
            <Button variant="outline" onClick={logout} type="button">
              <LogOut className="mr-2 h-4 w-4" />
              Log out
            </Button>
          </div>
        </header>

        {error ? (
          <Alert variant="destructive">
            <AlertTitle>Device detail error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card className="rounded-2xl shadow-sm">
            <CardContent className="flex items-center justify-between p-6">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Status</p>
                <Badge variant={getStatusVariant(detail?.device.status ?? "offline")}>
                  {detail?.device.status ?? "unknown"}
                </Badge>
              </div>
              <div className="rounded-2xl border bg-muted p-3">
                <Cpu className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-2xl shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground">Model</p>
              <p className="mt-1 text-lg font-medium">{detail?.device.model ?? "Loading..."}</p>
            </CardContent>
          </Card>

          <Card className="rounded-2xl shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground">Firmware</p>
              <p className="mt-1 text-lg font-medium">{detail?.device.fw_version ?? "unknown"}</p>
            </CardContent>
          </Card>

          <Card className="rounded-2xl shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground">Last seen</p>
              <p className="mt-1 text-sm font-medium">{formatDate(detail?.device.last_seen_at)}</p>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-6 xl:grid-cols-3">
          <Card className="rounded-3xl xl:col-span-2">
            <CardHeader>
              <CardTitle>Entities</CardTitle>
              <CardDescription>
                Latest known state for every capability projected from this device.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {loading && !detail ? (
                <>
                  <Card className="rounded-2xl border shadow-none">
                    <CardContent className="p-4">Loading...</CardContent>
                  </Card>
                </>
              ) : (
                detail?.entities.map((entity) => (
                  <Card className="rounded-2xl border shadow-none" key={entity.id}>
                    <CardContent className="space-y-2 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="font-medium">{entity.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {entity.id} | {entity.kind}
                          </div>
                        </div>
                        <Badge variant={entity.writable === 1 ? "default" : "outline"}>
                          {entity.writable === 1 ? "writable" : "read-only"}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {formatState(entity.state)}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        source: {entity.state_source ?? "n/a"} | updated:{" "}
                        {formatDate(entity.state_updated_at)} | version:{" "}
                        {entity.state_version ?? "n/a"}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle>Recent audit</CardTitle>
              <CardDescription>
                Latest events for this device and its projected entities.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {detail?.audit_events.length ? (
                detail.audit_events.map((event) => (
                  <div className="space-y-3 rounded-2xl border p-4" key={event.id}>
                    <div className="flex items-start justify-between gap-3">
                      <Badge
                        variant={event.severity === "warning" ? "secondary" : "default"}
                      >
                        {event.action}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(event.created_at)}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      target: {event.target_id ?? "n/a"} | actor: {event.actor_id ?? "system"}
                    </div>
                    <Textarea
                      className="min-h-[120px] font-mono text-xs"
                      readOnly
                      value={JSON.stringify(parseMetadata(event.metadata_json), null, 2)}
                    />
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No recent audit events.</p>
              )}
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}
