"use client";

import { useEffect, useEffectEvent, useMemo, useState } from "react";

import { AppShell } from "@/components/dashboard/app-shell";
import { AssistantConsole } from "@/components/dashboard/assistant-console";
import { AuthRequiredCard } from "@/components/dashboard/auth-required-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  apiFetch,
  AuditEvent,
  AutoLightSettings,
  Device,
  Entity,
  EntityState,
  formatDate,
  formatState,
  formatUserSubtitle,
  resolveApiBaseUrl,
  resolveAssistantBaseUrl,
  User,
} from "@/lib/alice-client";
import { useDashboardToken } from "@/hooks/use-dashboard-token";

export default function AssistantPage() {
  const apiBaseUrl = useMemo(() => resolveApiBaseUrl(), []);
  const assistantBaseUrl = useMemo(() => resolveAssistantBaseUrl(), []);
  const { token, tokenReady, clearToken } = useDashboardToken();

  const [user, setUser] = useState<User | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [states, setStates] = useState<Record<string, EntityState>>({});
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [autoLight, setAutoLight] = useState<AutoLightSettings | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadRuntime = async () => {
    if (!token) {
      return;
    }

    try {
      const [me, deviceResponse, entityResponse, stateResponse, auditResponse, autoLightResponse] =
        await Promise.all([
          apiFetch<User>(apiBaseUrl, "/auth/me", token),
          apiFetch<{ items: Device[] }>(apiBaseUrl, "/devices", token),
          apiFetch<{ items: Entity[] }>(apiBaseUrl, "/entities", token),
          apiFetch<{ items: EntityState[] }>(apiBaseUrl, "/entities/states", token),
          apiFetch<{ items: AuditEvent[] }>(apiBaseUrl, "/audit-events?limit=8", token),
          apiFetch<AutoLightSettings>(apiBaseUrl, "/system/auto-light", token),
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
      setError(null);
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "Failed to load runtime memory",
      );
    }
  };
  const refreshRuntime = useEffectEvent(() => void loadRuntime());

  useEffect(() => {
    if (!tokenReady || !token) {
      return;
    }

    const timeout = window.setTimeout(() => void refreshRuntime(), 0);
    const interval = window.setInterval(() => void refreshRuntime(), 10000);
    return () => {
      window.clearTimeout(timeout);
      window.clearInterval(interval);
    };
  }, [tokenReady, token, apiBaseUrl]);

  if (!tokenReady) {
    return null;
  }

  if (!token) {
    return (
      <AuthRequiredCard description="Return to the dashboard and sign in before opening the assistant console." />
    );
  }

  const onlineDevices = devices.filter((device) => device.status === "online").length;
  const writableEntities = entities.filter((entity) => entity.writable === 1).length;
  const recentStateEntries = Object.values(states)
    .sort(
      (left, right) =>
        new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
    )
    .slice(0, 5);

  return (
    <AppShell
      title="Assistant"
      description="Live browser-based assistant console with session memory and runtime context."
      subtitle={formatUserSubtitle(user)}
      onLogout={clearToken}
    >
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Assistant page error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(320px,0.9fr)]">
        <AssistantConsole
          assistantBaseUrl={assistantBaseUrl}
          onMutation={() => void loadRuntime()}
        />

        <div className="space-y-6">
          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle>Runtime memory</CardTitle>
              <CardDescription>
                Real-time house state the assistant is reasoning over.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-2xl border p-4">
                  <div className="text-xs text-muted-foreground">Online devices</div>
                  <div className="mt-2 text-2xl font-semibold">{onlineDevices}</div>
                </div>
                <div className="rounded-2xl border p-4">
                  <div className="text-xs text-muted-foreground">Writable entities</div>
                  <div className="mt-2 text-2xl font-semibold">{writableEntities}</div>
                </div>
              </div>

              <div className="rounded-2xl border p-4">
                <div className="text-sm font-medium">Automation memory</div>
                {autoLight ? (
                  <div className="mt-3 space-y-2 text-xs text-muted-foreground">
                    <div>enabled: {String(autoLight.enabled)}</div>
                    <div>mode: {autoLight.mode}</div>
                    <div>sensor: {autoLight.sensor_entity_id ?? "not set"}</div>
                    <div>target: {autoLight.target_entity_id ?? "not set"}</div>
                    <div>
                      thresholds: raw {autoLight.on_raw}/{autoLight.off_raw} | lux{" "}
                      {autoLight.on_lux}/{autoLight.off_lux}
                    </div>
                  </div>
                ) : null}
              </div>

              <div className="rounded-2xl border p-4">
                <div className="text-sm font-medium">Latest state changes</div>
                <div className="mt-3 space-y-3">
                  {recentStateEntries.map((entry) => (
                    <div key={entry.entity_id} className="rounded-xl border px-3 py-2">
                      <div className="text-xs font-medium">
                        {entities.find((entity) => entity.id === entry.entity_id)?.name ??
                          entry.entity_id}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {formatState(entry.value)}
                      </div>
                      <div className="mt-1 text-[11px] text-muted-foreground">
                        {formatDate(entry.updated_at)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border p-4">
                <div className="text-sm font-medium">Latest audit memory</div>
                <div className="mt-3 space-y-2">
                  {auditEvents.slice(0, 4).map((event) => (
                    <div key={event.id} className="text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">{event.action}</span>
                      {" | "}
                      {event.target_id ?? "n/a"}
                      {" | "}
                      {formatDate(event.created_at)}
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </AppShell>
  );
}

