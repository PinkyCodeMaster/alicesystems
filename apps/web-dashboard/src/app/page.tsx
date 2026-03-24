"use client";

import Link from "next/link";
import { FormEvent, useEffect, useEffectEvent, useMemo, useState } from "react";
import {
  Activity,
  Bot,
  Cpu,
  DoorOpen,
  Settings2,
  ShieldCheck,
  Zap,
} from "lucide-react";

import { AppShell } from "@/components/dashboard/app-shell";
import { AuditFeed } from "@/components/dashboard/audit-feed";
import { LoginCard } from "@/components/dashboard/login-card";
import { StatCard } from "@/components/dashboard/stat-card";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  apiFetch,
  assistantFetch,
  AuditEvent,
  AutoLightSettings,
  buildDashboardWebSocketUrl,
  Device,
  Entity,
  EntityState,
  formatCommandEventSummary,
  formatDate,
  formatState,
  formatUserSubtitle,
  HealthCheckState,
  HealthResponse,
  LoginResponse,
  resolveApiBaseUrl,
  resolveAssistantBaseUrl,
  StackHealth,
  User,
} from "@/lib/alice-client";
import { useDashboardToken } from "@/hooks/use-dashboard-token";

export default function OverviewPage() {
  const apiBaseUrl = useMemo(() => resolveApiBaseUrl(), []);
  const assistantBaseUrl = useMemo(() => resolveAssistantBaseUrl(), []);
  const { token, tokenReady, storeToken, clearToken } = useDashboardToken();

  const [loginEmail, setLoginEmail] = useState("admin@alice.systems");
  const [loginPassword, setLoginPassword] = useState("change-me");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const [hubHealth, setHubHealth] = useState<HealthCheckState>({
    status: "checking",
    message: "Checking hub health...",
  });
  const [assistantHealth, setAssistantHealth] = useState<HealthCheckState>({
    status: "checking",
    message: "Checking assistant health...",
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [states, setStates] = useState<Record<string, EntityState>>({});
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [autoLight, setAutoLight] = useState<AutoLightSettings | null>(null);
  const [stackHealth, setStackHealth] = useState<StackHealth | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadHubHealth = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/health`, {
          headers: { Accept: "application/json" },
        });
        if (!response.ok) {
          throw new Error(`${response.status} ${response.statusText}`);
        }
        const body = (await response.json()) as HealthResponse;
        if (cancelled) return;
        setHubHealth({
          status: "reachable",
          message: `${body.service} is ${body.status} (${body.environment})`,
        });
      } catch (nextError) {
        if (cancelled) return;
        setHubHealth({
          status: "unreachable",
          message:
            nextError instanceof Error
              ? nextError.message
              : "Health check failed",
        });
      }
    };

    const loadAssistantHealth = async () => {
      try {
        const body = await assistantFetch<HealthResponse>(
          assistantBaseUrl,
          "/health",
        );
        if (cancelled) return;
        setAssistantHealth({
          status: "reachable",
          message: `${body.service} is ${body.status} (${body.environment})`,
        });
      } catch (nextError) {
        if (cancelled) return;
        setAssistantHealth({
          status: "unreachable",
          message:
            nextError instanceof Error
              ? nextError.message
              : "Assistant health check failed",
        });
      }
    };

    void loadHubHealth();
    void loadAssistantHealth();
    const interval = window.setInterval(() => {
      void loadHubHealth();
      void loadAssistantHealth();
    }, 10000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [apiBaseUrl, assistantBaseUrl]);

  const loadOverview = useEffectEvent(async () => {
    if (!token) {
      setUser(null);
      setDevices([]);
      setEntities([]);
      setStates({});
      setAuditEvents([]);
      setAutoLight(null);
      setStackHealth(null);
      setLoading(false);
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
        apiFetch<{ items: EntityState[] }>(apiBaseUrl, "/entities/states", token),
        apiFetch<{ items: AuditEvent[] }>(apiBaseUrl, "/audit-events?limit=12", token),
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
      setError(null);
    } catch (nextError) {
      const message =
        nextError instanceof Error ? nextError.message : "Failed to load overview";
      setError(message);
      if (
        message.includes("401") ||
        message.includes("Invalid") ||
        message.includes("Missing bearer")
      ) {
        clearToken();
      }
    } finally {
      setLoading(false);
    }
  });

  useEffect(() => {
    if (!tokenReady) {
      return;
    }

    const timeout = window.setTimeout(() => void loadOverview(), 0);
    if (!token) {
      return () => window.clearTimeout(timeout);
    }

    const interval = window.setInterval(() => void loadOverview(), 30000);
    return () => {
      window.clearTimeout(timeout);
      window.clearInterval(interval);
    };
  }, [token, tokenReady, apiBaseUrl]);

  useEffect(() => {
    if (!token) {
      return;
    }

    const websocket = new WebSocket(buildDashboardWebSocketUrl(apiBaseUrl, token));
    websocket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type?: string };
        if (payload.type && payload.type !== "ping" && payload.type !== "connected") {
          void loadOverview();
        }
      } catch {
        void loadOverview();
      }
    };

    return () => websocket.close();
  }, [apiBaseUrl, token]);

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
      storeToken(body.access_token);
    } catch (nextError) {
      setLoginError(nextError instanceof Error ? nextError.message : "Login failed");
    } finally {
      setIsLoggingIn(false);
    }
  };

  const onlineDevices = devices.filter((device) => device.status === "online").length;
  const writableEntities = entities.filter((entity) => entity.writable === 1).length;
  const recentStateEntries = Object.values(states)
    .sort(
      (left, right) =>
        new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
    )
    .slice(0, 5);

  if (!token && tokenReady) {
    return (
      <LoginCard
        apiBaseUrl={apiBaseUrl}
        assistantBaseUrl={assistantBaseUrl}
        loginEmail={loginEmail}
        loginPassword={loginPassword}
        loginError={loginError}
        isLoggingIn={isLoggingIn}
        hubHealth={hubHealth}
        assistantHealth={assistantHealth}
        onSubmit={login}
        onEmailChange={setLoginEmail}
        onPasswordChange={setLoginPassword}
      />
    );
  }

  return (
    <AppShell
      title="House overview"
      description="Operational summary of the local Alice stack, with dedicated routes for assistant, devices, automation, and audit."
      subtitle={formatUserSubtitle(user)}
      onLogout={clearToken}
    >
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Overview error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Devices" value={devices.length} icon={Cpu} hint="Registered" />
        <StatCard title="Online" value={onlineDevices} icon={Activity} hint="Heartbeat detected" />
        <StatCard title="Entities" value={entities.length} icon={Zap} hint="Known capabilities" />
        <StatCard title="Writable" value={writableEntities} icon={ShieldCheck} hint="Direct control enabled" />
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <Card className="rounded-3xl xl:col-span-2">
          <CardHeader>
            <CardTitle>Stack health</CardTitle>
            <CardDescription>
              API, broker, devices, and the latest command request/ack.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading && !stackHealth ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <Skeleton className="h-28 rounded-2xl" />
                <Skeleton className="h-28 rounded-2xl" />
                <Skeleton className="h-28 rounded-2xl" />
                <Skeleton className="h-28 rounded-2xl" />
              </div>
            ) : stackHealth ? (
              <div className="space-y-4">
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
                  </div>

                  <div className="rounded-2xl border p-4">
                    <div className="text-sm text-muted-foreground">Latest relay ack</div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      {formatCommandEventSummary(stackHealth.latest_command_ack)}
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      {formatDate(stackHealth.latest_command_ack?.created_at)}
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border p-4">
                    <div className="text-sm font-medium">Latest command request</div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      {formatCommandEventSummary(stackHealth.latest_command_request)}
                    </div>
                  </div>
                  <div className="rounded-2xl border p-4">
                    <div className="text-sm font-medium">Latest command acknowledgement</div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      {formatCommandEventSummary(stackHealth.latest_command_ack)}
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle>Reachability</CardTitle>
            <CardDescription>
              Browser connectivity to both hub and assistant runtimes.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border p-4">
              <div className="text-xs text-muted-foreground">Hub target</div>
              <div className="mt-1 text-sm break-all">{apiBaseUrl}</div>
              <div className="mt-2 flex items-center gap-2">
                <Badge variant={hubHealth.status === "reachable" ? "default" : hubHealth.status === "checking" ? "secondary" : "destructive"}>
                  {hubHealth.status}
                </Badge>
                <span className="text-xs text-muted-foreground">{hubHealth.message}</span>
              </div>
            </div>
            <div className="rounded-2xl border p-4">
              <div className="text-xs text-muted-foreground">Assistant target</div>
              <div className="mt-1 text-sm break-all">{assistantBaseUrl}</div>
              <div className="mt-2 flex items-center gap-2">
                <Badge variant={assistantHealth.status === "reachable" ? "default" : assistantHealth.status === "checking" ? "secondary" : "destructive"}>
                  {assistantHealth.status}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {assistantHealth.message}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-4">
        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-4 w-4" />
              Assistant
            </CardTitle>
            <CardDescription>Live session memory and tool traces.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/assistant">
              <Button className="w-full">Open assistant page</Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-4 w-4" />
              Devices
            </CardTitle>
            <CardDescription>Hardware list and current entity state.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/devices">
              <Button className="w-full" variant="outline">
                Open devices page
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings2 className="h-4 w-4" />
              Auto-light
            </CardTitle>
            <CardDescription>Thresholds, mapping, and automation state.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/automations/auto-light">
              <Button className="w-full" variant="outline">
                Open automation page
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DoorOpen className="h-4 w-4" />
              Audit
            </CardTitle>
            <CardDescription>Recent state changes, commands, and acknowledgements.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/audit">
              <Button className="w-full" variant="outline">
                Open audit page
              </Button>
            </Link>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle>Automation snapshot</CardTitle>
            <CardDescription>
              Current canonical auto-light state from Home OS.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            {autoLight ? (
              <>
                <div>enabled: {String(autoLight.enabled)}</div>
                <div>mode: {autoLight.mode}</div>
                <div>sensor: {autoLight.sensor_entity_id ?? "not set"}</div>
                <div>target: {autoLight.target_entity_id ?? "not set"}</div>
                <div>
                  thresholds: raw {autoLight.on_raw}/{autoLight.off_raw} | lux{" "}
                  {autoLight.on_lux}/{autoLight.off_lux}
                </div>
              </>
            ) : (
              <Skeleton className="h-24 rounded-2xl" />
            )}
          </CardContent>
        </Card>

        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle>Latest state changes</CardTitle>
            <CardDescription>
              Most recent entity state updates projected into Home OS.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {recentStateEntries.length === 0 ? (
              <p className="text-sm text-muted-foreground">No state entries yet.</p>
            ) : (
              recentStateEntries.map((entry) => (
                <div key={entry.entity_id} className="rounded-2xl border p-4">
                  <div className="text-sm font-medium">
                    {entities.find((entity) => entity.id === entry.entity_id)?.name ??
                      entry.entity_id}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {formatState(entry.value)}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {formatDate(entry.updated_at)}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle>Recent audit</CardTitle>
            <CardDescription>Compact audit summary for the latest events.</CardDescription>
          </CardHeader>
          <CardContent>
            <AuditFeed
              events={auditEvents.slice(0, 4)}
              emptyMessage="No recent audit events."
            />
          </CardContent>
        </Card>
      </section>
    </AppShell>
  );
}

