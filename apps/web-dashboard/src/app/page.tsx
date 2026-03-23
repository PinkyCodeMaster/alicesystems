"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  Cpu,
  DoorOpen,
  LogOut,
  Settings2,
  ShieldCheck,
  Zap,
} from "lucide-react";

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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";

type LoginResponse = {
  access_token: string;
  token_type: string;
  user_id: string;
  display_name: string;
};

type User = {
  id: string;
  email: string;
  display_name: string;
  role: string;
};

type Device = {
  id: string;
  name: string;
  model: string;
  device_type: string;
  status: string;
  fw_version: string | null;
  last_seen_at: string | null;
};

type Entity = {
  id: string;
  device_id: string;
  capability_id: string;
  kind: string;
  name: string;
  writable: number;
};

type EntityState = {
  entity_id: string;
  value: Record<string, unknown>;
  source: string;
  updated_at: string;
  version: number;
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

type AutoLightSettings = {
  enabled: boolean;
  sensor_entity_id: string | null;
  target_entity_id: string | null;
  mode: string;
  on_lux: number;
  off_lux: number;
  on_raw: number;
  off_raw: number;
  source: string;
  updated_at: string | null;
};

type StackHealthBroker = {
  enabled: boolean;
  host: string;
  port: number;
  started: boolean;
  connected: boolean;
};

type StackHealthDevices = {
  total: number;
  online: number;
  offline: number;
  timeout_seconds: number;
};

type StackHealthCommandEvent = {
  action: string;
  target_id: string | null;
  actor_id: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
};

type StackHealth = {
  api_status: string;
  api_service: string;
  environment: string;
  broker: StackHealthBroker;
  devices: StackHealthDevices;
  latest_command_request: StackHealthCommandEvent | null;
  latest_command_ack: StackHealthCommandEvent | null;
};

type HealthResponse = {
  status: string;
  service: string;
  environment: string;
};

type HealthCheckState = {
  status: "checking" | "reachable" | "unreachable";
  message: string;
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

function parseMetadata(value: string): Record<string, unknown> {
  try {
    return JSON.parse(value);
  } catch {
    return {};
  }
}

function formatState(value?: Record<string, unknown>): string {
  if (!value) return "No state";
  return Object.entries(value)
    .map(([key, entry]) => `${key}: ${String(entry)}`)
    .join(" · ");
}

function formatDate(value?: string | null): string {
  if (!value) return "Never";
  return new Date(value).toLocaleString();
}

function formatCommandEventSummary(event: StackHealthCommandEvent | null): string {
  if (!event) return "No recent event";

  const command = String(event.metadata.command ?? "unknown");
  const status = event.metadata.status ? ` | ${String(event.metadata.status)}` : "";
  const target = event.target_id ? ` | ${event.target_id}` : "";
  return `${command}${status}${target}`;
}

function buildDashboardWebSocketUrl(apiBaseUrl: string, token: string): string {
  const origin = apiBaseUrl.replace(/\/api\/v1$/, "");
  return `${origin.replace(/^http/, "ws")}/api/v1/ws/dashboard?token=${encodeURIComponent(token)}`;
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

async function apiFetch<T>(
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

function StatCard({
  title,
  value,
  icon: Icon,
  hint,
}: {
  title: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  hint?: string;
}) {
  return (
    <Card className="rounded-2xl shadow-sm">
      <CardContent className="flex items-center justify-between p-6">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-3xl font-semibold tracking-tight">{value}</p>
          {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
        </div>
        <div className="rounded-2xl border bg-muted p-3">
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const apiBaseUrl = useMemo(() => resolveApiBaseUrl(), []);
  const [token, setToken] = useState<string | null>(null);

  const [loginEmail, setLoginEmail] = useState("admin@alice.systems");
  const [loginPassword, setLoginPassword] = useState("change-me");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [states, setStates] = useState<Record<string, EntityState>>({});
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [autoLight, setAutoLight] = useState<AutoLightSettings | null>(null);
  const [stackHealth, setStackHealth] = useState<StackHealth | null>(null);

  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [busyEntityId, setBusyEntityId] = useState<string | null>(null);
  const [savingAutoLight, setSavingAutoLight] = useState(false);
  const [healthCheck, setHealthCheck] = useState<HealthCheckState>({
    status: "checking",
    message: "Checking hub health...",
  });

  useEffect(() => {
    const stored = window.localStorage.getItem(TOKEN_KEY);
    if (stored) {
      setToken(stored);
    } else {
      setIsBootstrapping(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const checkHealth = async () => {
      setHealthCheck({
        status: "checking",
        message: "Checking hub health...",
      });

      try {
        const response = await fetch(`${apiBaseUrl}/health`, {
          headers: { Accept: "application/json" },
        });

        if (!response.ok) {
          throw new Error(`${response.status} ${response.statusText}`);
        }

        const body = (await response.json()) as HealthResponse;
        if (cancelled) {
          return;
        }

        setHealthCheck({
          status: "reachable",
          message: `${body.service} is ${body.status} (${body.environment})`,
        });
      } catch (error) {
        if (cancelled) {
          return;
        }

        const message =
          error instanceof Error ? error.message : "Health check failed";
        setHealthCheck({
          status: "unreachable",
          message,
        });
      }
    };

    void checkHealth();
    const interval = window.setInterval(() => void checkHealth(), 10000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [apiBaseUrl]);

  const loadDashboard = useCallback(async () => {
    if (!token) {
      setUser(null);
      setDevices([]);
      setEntities([]);
      setStates({});
      setAuditEvents([]);
      setAutoLight(null);
      setStackHealth(null);
      setIsBootstrapping(false);
      return;
    }

    try {
      const [
        me,
        deviceResponse,
        entityResponse,
        stateResponse,
        auditResponse,
        autoLightResponse,
        stackHealthResponse,
      ] = await Promise.all([
        apiFetch<User>(apiBaseUrl, "/auth/me", token),
        apiFetch<{ items: Device[] }>(apiBaseUrl, "/devices", token),
        apiFetch<{ items: Entity[] }>(apiBaseUrl, "/entities", token),
        apiFetch<{ items: EntityState[] }>(
          apiBaseUrl,
          "/entities/states",
          token,
        ),
        apiFetch<{ items: AuditEvent[] }>(
          apiBaseUrl,
          "/audit-events?limit=25",
          token,
        ),
        apiFetch<AutoLightSettings>(apiBaseUrl, "/system/auto-light", token),
        apiFetch<StackHealth>(apiBaseUrl, "/system/stack-health", token),
      ]);

      setUser(me);
      setDevices(deviceResponse.items);
      setEntities(entityResponse.items);
      setStates(
        Object.fromEntries(
          stateResponse.items.map((item) => [item.entity_id, item]),
        ),
      );
      setAuditEvents(auditResponse.items);
      setAutoLight(autoLightResponse);
      setStackHealth(stackHealthResponse);
      setDashboardError(null);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unknown dashboard error";

      setDashboardError(message);

      if (
        message.includes("401") ||
        message.includes("Invalid") ||
        message.includes("Missing bearer")
      ) {
        window.localStorage.removeItem(TOKEN_KEY);
        setToken(null);
      }
    } finally {
      setIsBootstrapping(false);
    }
  }, [apiBaseUrl, token]);

  useEffect(() => {
    void loadDashboard();
    if (!token) {
      return;
    }

    const interval = window.setInterval(() => void loadDashboard(), 30000);
    return () => window.clearInterval(interval);
  }, [loadDashboard, token]);

  useEffect(() => {
    if (!token) {
      return;
    }

    const websocket = new WebSocket(buildDashboardWebSocketUrl(apiBaseUrl, token));
    websocket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type?: string };
        if (payload.type && payload.type !== "ping" && payload.type !== "connected") {
          void loadDashboard();
        }
      } catch {
        void loadDashboard();
      }
    };

    websocket.onerror = () => {
      // Keep the fallback polling path active even if WS is unavailable.
    };

    return () => {
      websocket.close();
    };
  }, [apiBaseUrl, loadDashboard, token]);

  const login = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoggingIn(true);
    setLoginError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          email: loginEmail,
          password: loginPassword,
        }),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const body = (await response.json()) as LoginResponse;
      window.localStorage.setItem(TOKEN_KEY, body.access_token);
      setToken(body.access_token);
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "Login failed");
    } finally {
      setIsLoggingIn(false);
    }
  };

  const logout = () => {
    window.localStorage.removeItem(TOKEN_KEY);
    setToken(null);
  };

  const sendRelayCommand = async (entityId: string, on: boolean) => {
    if (!token) return;
    setBusyEntityId(entityId);

    try {
      await apiFetch(apiBaseUrl, `/entities/${entityId}/commands`, token, {
        method: "POST",
        body: JSON.stringify({
          command: "switch.set",
          params: { on },
        }),
      });
      setDashboardError(null);
    } catch (error) {
      setDashboardError(
        error instanceof Error ? error.message : "Relay command failed",
      );
    } finally {
      setBusyEntityId(null);
    }
  };

  const saveAutoLight = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !autoLight) return;

    setSavingAutoLight(true);

    try {
      const updated = await apiFetch<AutoLightSettings>(
        apiBaseUrl,
        "/system/auto-light",
        token,
        {
          method: "PUT",
          body: JSON.stringify(autoLight),
        },
      );

      setAutoLight(updated);
      setDashboardError(null);
    } catch (error) {
      setDashboardError(
        error instanceof Error ? error.message : "Failed to save auto-light",
      );
    } finally {
      setSavingAutoLight(false);
    }
  };

  const writableEntities = useMemo(
    () => entities.filter((entity) => entity.writable === 1),
    [entities],
  );

  const onlineDevices = useMemo(
    () => devices.filter((device) => device.status === "online").length,
    [devices],
  );

  if (!token) {
    return (
      <main className="min-h-screen bg-background">
        <div className="mx-auto flex min-h-screen max-w-6xl items-center justify-center px-4">
          <Card className="w-full max-w-md rounded-3xl border shadow-lg">
            <CardHeader className="space-y-3">
              <div className="flex items-center justify-between">
                <Badge variant="secondary" className="rounded-full px-3 py-1">
                  Alice Home OS
                </Badge>
                <ModeToggle />
              </div>
              <div>
                <CardTitle className="text-2xl">Local dashboard login</CardTitle>
                <CardDescription className="pt-1">
                  Sign in with your local admin account to inspect devices,
                  states, automations, and audit events.
                </CardDescription>
                <div className="pt-3 text-xs text-muted-foreground">
                  API target: {apiBaseUrl}
                </div>
                <div className="pt-2">
                  <Badge
                    variant={
                      healthCheck.status === "reachable"
                        ? "default"
                        : healthCheck.status === "checking"
                          ? "secondary"
                          : "destructive"
                    }
                  >
                    Hub health: {healthCheck.status}
                  </Badge>
                  <div className="pt-2 text-xs text-muted-foreground">
                    {healthCheck.message}
                  </div>
                </div>
              </div>
            </CardHeader>

            <CardContent>
              <form className="space-y-4" onSubmit={login}>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    autoComplete="email"
                    value={loginEmail}
                    onChange={(event) => setLoginEmail(event.target.value)}
                    placeholder="admin@alice.systems"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    value={loginPassword}
                    onChange={(event) => setLoginPassword(event.target.value)}
                    placeholder="••••••••"
                  />
                </div>

                {loginError ? (
                  <Alert variant="destructive">
                    <AlertTitle>Login failed</AlertTitle>
                    <AlertDescription>{loginError}</AlertDescription>
                  </Alert>
                ) : null}

                <Button className="w-full" disabled={isLoggingIn} type="submit">
                  {isLoggingIn ? "Signing in..." : "Sign in"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 md:px-6 lg:px-8">
        <header className="flex flex-col gap-4 rounded-3xl border bg-card p-6 shadow-sm md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <Badge variant="secondary" className="rounded-full px-3 py-1">
              Alice Dashboard
            </Badge>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">
                House runtime view
              </h1>
              <p className="text-sm text-muted-foreground">
                Local control plane for devices, entities, automation, and audit
                activity.
              </p>
            </div>
          </div>

          <div className="flex flex-col items-start gap-3 md:items-end">
            <div className="text-sm text-muted-foreground">
              {user
                ? `${user.display_name} · ${user.email} · ${user.role}`
                : "Loading user..."}
            </div>
            <div className="flex items-center gap-2">
              <ModeToggle />
              <Button variant="outline" onClick={logout} type="button">
                <LogOut className="mr-2 h-4 w-4" />
                Log out
              </Button>
            </div>
          </div>
        </header>

        {dashboardError ? (
          <Alert variant="destructive">
            <AlertTitle>Dashboard error</AlertTitle>
            <AlertDescription>{dashboardError}</AlertDescription>
          </Alert>
        ) : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            title="Devices"
            value={devices.length}
            icon={Cpu}
            hint="Registered on this slice"
          />
          <StatCard
            title="Online"
            value={onlineDevices}
            icon={Activity}
            hint="Heartbeat detected"
          />
          <StatCard
            title="Entities"
            value={entities.length}
            icon={Zap}
            hint="Available capabilities"
          />
          <StatCard
            title="Writable"
            value={writableEntities.length}
            icon={ShieldCheck}
            hint="Direct control enabled"
          />
        </section>

        <section className="grid gap-6 xl:grid-cols-3">
          <Card className="rounded-3xl xl:col-span-2">
            <CardHeader>
              <CardTitle>Stack health</CardTitle>
              <CardDescription>
                One place to see API, broker, device, and command acknowledgement status.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {stackHealth ? (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-2xl border p-4">
                    <div className="text-sm text-muted-foreground">API</div>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge variant={stackHealth.api_status === "ok" ? "default" : "destructive"}>
                        {stackHealth.api_status}
                      </Badge>
                      <span className="text-sm">{stackHealth.api_service}</span>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      environment: {stackHealth.environment}
                    </div>
                  </div>

                  <div className="rounded-2xl border p-4">
                    <div className="text-sm text-muted-foreground">Broker</div>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge
                        variant={
                          stackHealth.broker.connected
                            ? "default"
                            : stackHealth.broker.started
                              ? "secondary"
                              : "outline"
                        }
                      >
                        {stackHealth.broker.connected ? "connected" : "disconnected"}
                      </Badge>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      {stackHealth.broker.host}:{stackHealth.broker.port}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      enabled: {String(stackHealth.broker.enabled)} | started:{" "}
                      {String(stackHealth.broker.started)}
                    </div>
                  </div>

                  <div className="rounded-2xl border p-4">
                    <div className="text-sm text-muted-foreground">Devices</div>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge variant={stackHealth.devices.online > 0 ? "default" : "outline"}>
                        {stackHealth.devices.online} online
                      </Badge>
                      <Badge variant="outline">{stackHealth.devices.offline} offline</Badge>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      total: {stackHealth.devices.total}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      timeout: {stackHealth.devices.timeout_seconds}s
                    </div>
                  </div>

                  <div className="rounded-2xl border p-4">
                    <div className="text-sm text-muted-foreground">Latest relay ack</div>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge
                        variant={
                          stackHealth.latest_command_ack?.metadata?.status === "applied"
                            ? "default"
                            : stackHealth.latest_command_ack
                              ? "secondary"
                              : "outline"
                        }
                      >
                        {stackHealth.latest_command_ack?.metadata?.status
                          ? String(stackHealth.latest_command_ack.metadata.status)
                          : "none"}
                      </Badge>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      {formatCommandEventSummary(stackHealth.latest_command_ack)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatDate(stackHealth.latest_command_ack?.created_at)}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <Skeleton className="h-28 rounded-2xl" />
                  <Skeleton className="h-28 rounded-2xl" />
                  <Skeleton className="h-28 rounded-2xl" />
                  <Skeleton className="h-28 rounded-2xl" />
                </div>
              )}

              <Separator className="my-4" />

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border p-4">
                  <div className="text-sm font-medium">Latest command request</div>
                  <div className="mt-2 text-sm text-muted-foreground">
                    {formatCommandEventSummary(stackHealth?.latest_command_request ?? null)}
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    actor: {stackHealth?.latest_command_request?.actor_id ?? "n/a"}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    time: {formatDate(stackHealth?.latest_command_request?.created_at)}
                  </div>
                </div>

                <div className="rounded-2xl border p-4">
                  <div className="text-sm font-medium">Latest command acknowledgement</div>
                  <div className="mt-2 text-sm text-muted-foreground">
                    {formatCommandEventSummary(stackHealth?.latest_command_ack ?? null)}
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    actor: {stackHealth?.latest_command_ack?.actor_id ?? "n/a"}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    time: {formatDate(stackHealth?.latest_command_ack?.created_at)}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DoorOpen className="h-4 w-4" />
                Runtime reachability
              </CardTitle>
              <CardDescription>
                Browser-to-hub connectivity before and after login.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <div className="text-xs text-muted-foreground">API target</div>
                <div className="text-sm break-all">{apiBaseUrl}</div>
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  variant={
                    healthCheck.status === "reachable"
                      ? "default"
                      : healthCheck.status === "checking"
                        ? "secondary"
                        : "destructive"
                  }
                >
                  {healthCheck.status}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {healthCheck.message}
                </span>
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-6 xl:grid-cols-3">
          <Card className="rounded-3xl xl:col-span-2">
            <CardHeader>
              <CardTitle>Devices</CardTitle>
              <CardDescription>
                Heartbeat status, firmware, and last-seen details for current
                boards.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isBootstrapping ? (
                <div className="space-y-3">
                  <Skeleton className="h-12 w-full rounded-xl" />
                  <Skeleton className="h-12 w-full rounded-xl" />
                  <Skeleton className="h-12 w-full rounded-xl" />
                </div>
              ) : (
                <div className="overflow-x-auto rounded-2xl border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Last seen</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {devices.map((device) => (
                        <TableRow key={device.id}>
                          <TableCell className="min-w-[280px] align-top">
                            <Link
                              className="font-medium underline-offset-4 hover:underline"
                              href={`/devices/${device.id}`}
                            >
                              {device.name}
                            </Link>
                            <div className="text-xs text-muted-foreground">
                              {device.id} · {device.model} · fw{" "}
                              {device.fw_version ?? "unknown"}
                            </div>
                          </TableCell>
                          <TableCell>{device.device_type}</TableCell>
                          <TableCell>
                            <Badge variant={getStatusVariant(device.status)}>
                              {device.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{formatDate(device.last_seen_at)}</TableCell>
                        </TableRow>
                      ))}
                      {devices.length === 0 ? (
                        <TableRow>
                          <TableCell
                            colSpan={4}
                            className="text-center text-muted-foreground"
                          >
                            No devices found.
                          </TableCell>
                        </TableRow>
                      ) : null}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings2 className="h-4 w-4" />
                Auto-light
              </CardTitle>
              <CardDescription>
                Stored in SQLite and editable without touching environment
                config.
              </CardDescription>
            </CardHeader>

            <CardContent>
              {autoLight ? (
                <form className="space-y-4" onSubmit={saveAutoLight}>
                  <div className="flex items-center justify-between rounded-2xl border p-4">
                    <div>
                      <Label htmlFor="enabled" className="text-sm font-medium">
                        Enabled
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        Toggle the automation on or off.
                      </p>
                    </div>
                    <Switch
                      id="enabled"
                      checked={autoLight.enabled}
                      onCheckedChange={(checked) =>
                        setAutoLight({ ...autoLight, enabled: checked })
                      }
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Mode</Label>
                    <Select
                      value={autoLight.mode}
                      onValueChange={(value) =>
                        setAutoLight({ ...autoLight, mode: value || '' })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select mode" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="lux_low_turn_on">
                          lux_low_turn_on
                        </SelectItem>
                        <SelectItem value="raw_high_turn_on">
                          raw_high_turn_on
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="sensor_entity_id">Sensor entity</Label>
                      <Input
                        id="sensor_entity_id"
                        value={autoLight.sensor_entity_id ?? ""}
                        onChange={(event) =>
                          setAutoLight({
                            ...autoLight,
                            sensor_entity_id: event.target.value || null,
                          })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="target_entity_id">Target entity</Label>
                      <Input
                        id="target_entity_id"
                        value={autoLight.target_entity_id ?? ""}
                        onChange={(event) =>
                          setAutoLight({
                            ...autoLight,
                            target_entity_id: event.target.value || null,
                          })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="on_raw">On raw</Label>
                      <Input
                        id="on_raw"
                        type="number"
                        value={autoLight.on_raw}
                        onChange={(event) =>
                          setAutoLight({
                            ...autoLight,
                            on_raw: Number(event.target.value),
                          })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="off_raw">Off raw</Label>
                      <Input
                        id="off_raw"
                        type="number"
                        value={autoLight.off_raw}
                        onChange={(event) =>
                          setAutoLight({
                            ...autoLight,
                            off_raw: Number(event.target.value),
                          })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="on_lux">On lux</Label>
                      <Input
                        id="on_lux"
                        type="number"
                        value={autoLight.on_lux}
                        onChange={(event) =>
                          setAutoLight({
                            ...autoLight,
                            on_lux: Number(event.target.value),
                          })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="off_lux">Off lux</Label>
                      <Input
                        id="off_lux"
                        type="number"
                        value={autoLight.off_lux}
                        onChange={(event) =>
                          setAutoLight({
                            ...autoLight,
                            off_lux: Number(event.target.value),
                          })
                        }
                      />
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-1 text-xs text-muted-foreground">
                    <p>Source: {autoLight.source}</p>
                    <p>Updated: {formatDate(autoLight.updated_at)}</p>
                  </div>

                  <Button className="w-full" disabled={savingAutoLight} type="submit">
                    {savingAutoLight ? "Saving..." : "Save auto-light"}
                  </Button>
                </form>
              ) : (
                <div className="space-y-3">
                  <Skeleton className="h-10 w-full rounded-xl" />
                  <Skeleton className="h-10 w-full rounded-xl" />
                  <Skeleton className="h-10 w-full rounded-xl" />
                  <Skeleton className="h-10 w-full rounded-xl" />
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-3xl xl:col-span-2">
            <CardHeader>
              <CardTitle>Entities</CardTitle>
              <CardDescription>
                Current state and direct control for writable entities.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto rounded-2xl border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Entity</TableHead>
                      <TableHead>Capability</TableHead>
                      <TableHead>State</TableHead>
                      <TableHead className="w-[180px]">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {entities.map((entity) => (
                      <TableRow key={entity.id}>
                        <TableCell className="align-top">
                          <div className="font-medium">{entity.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {entity.id} · {entity.device_id}
                          </div>
                        </TableCell>
                        <TableCell>{entity.kind}</TableCell>
                        <TableCell className="max-w-[360px] text-sm text-muted-foreground">
                          {formatState(states[entity.id]?.value)}
                        </TableCell>
                        <TableCell>
                          {entity.writable === 1 ? (
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                disabled={busyEntityId === entity.id}
                                onClick={() => void sendRelayCommand(entity.id, true)}
                                type="button"
                              >
                                On
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={busyEntityId === entity.id}
                                onClick={() => void sendRelayCommand(entity.id, false)}
                                type="button"
                              >
                                Off
                              </Button>
                            </div>
                          ) : (
                            <Badge variant="outline">Read-only</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}

                    {entities.length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={4}
                          className="text-center text-muted-foreground"
                        >
                          No entities found.
                        </TableCell>
                      </TableRow>
                    ) : null}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DoorOpen className="h-4 w-4" />
                Recent audit
              </CardTitle>
              <CardDescription>
                Latest state changes, commands, and acknowledgements.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {auditEvents.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No recent audit events.
                </p>
              ) : (
                auditEvents.map((event) => {
                  const metadata = parseMetadata(event.metadata_json);

                  return (
                    <div
                      key={event.id}
                      className="space-y-3 rounded-2xl border p-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <Badge
                            variant={
                              event.severity === "warning"
                                ? "secondary"
                                : "default"
                            }
                          >
                            {event.action}
                          </Badge>
                          <p className="text-xs text-muted-foreground">
                            {formatDate(event.created_at)}
                          </p>
                        </div>
                      </div>

                      <div className="text-xs text-muted-foreground">
                        target: {event.target_id ?? "n/a"} · actor:{" "}
                        {event.actor_id ?? "system"}
                      </div>

                      <Textarea
                        readOnly
                        value={JSON.stringify(metadata, null, 2)}
                        className="min-h-[120px] font-mono text-xs"
                      />
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}
