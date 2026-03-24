"use client";

import { useEffect, useEffectEvent, useMemo, useState } from "react";

import { AppShell } from "@/components/dashboard/app-shell";
import { AuthRequiredCard } from "@/components/dashboard/auth-required-card";
import { DevicesTable } from "@/components/dashboard/devices-table";
import { EntitiesTable } from "@/components/dashboard/entities-table";
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
  buildDashboardWebSocketUrl,
  Device,
  Entity,
  EntityState,
  formatUserSubtitle,
  resolveApiBaseUrl,
  User,
} from "@/lib/alice-client";
import { useDashboardToken } from "@/hooks/use-dashboard-token";

export default function DevicesPage() {
  const apiBaseUrl = useMemo(() => resolveApiBaseUrl(), []);
  const { token, tokenReady, clearToken } = useDashboardToken();

  const [user, setUser] = useState<User | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [states, setStates] = useState<Record<string, EntityState>>({});
  const [error, setError] = useState<string | null>(null);
  const [busyEntityId, setBusyEntityId] = useState<string | null>(null);

  const loadDevices = async () => {
    if (!token) {
      return;
    }

    try {
      const [me, deviceResponse, entityResponse, stateResponse] = await Promise.all([
        apiFetch<User>(apiBaseUrl, "/auth/me", token),
        apiFetch<{ items: Device[] }>(apiBaseUrl, "/devices", token),
        apiFetch<{ items: Entity[] }>(apiBaseUrl, "/entities", token),
        apiFetch<{ items: EntityState[] }>(apiBaseUrl, "/entities/states", token),
      ]);

      setUser(me);
      setDevices(deviceResponse.items);
      setEntities(entityResponse.items);
      setStates(
        Object.fromEntries(
          stateResponse.items.map((item) => [item.entity_id, item]),
        ),
      );
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to load devices");
    }
  };
  const refreshDevices = useEffectEvent(() => void loadDevices());

  useEffect(() => {
    if (!tokenReady || !token) {
      return;
    }

    const timeout = window.setTimeout(() => void refreshDevices(), 0);
    const interval = window.setInterval(() => void refreshDevices(), 30000);
    return () => {
      window.clearTimeout(timeout);
      window.clearInterval(interval);
    };
  }, [tokenReady, token, apiBaseUrl]);

  useEffect(() => {
    if (!token) {
      return;
    }

    const websocket = new WebSocket(buildDashboardWebSocketUrl(apiBaseUrl, token));
    websocket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type?: string };
        if (payload.type && payload.type !== "ping" && payload.type !== "connected") {
          void refreshDevices();
        }
      } catch {
        void refreshDevices();
      }
    };

    return () => websocket.close();
  }, [apiBaseUrl, token]);

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
      await loadDevices();
      setError(null);
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "Relay command failed",
      );
    } finally {
      setBusyEntityId(null);
    }
  };

  if (!tokenReady) {
    return null;
  }

  if (!token) {
    return <AuthRequiredCard description="Return to the dashboard and sign in before opening devices." />;
  }

  return (
    <AppShell
      title="Devices"
      description="Hardware inventory, device status, and current entity state."
      subtitle={formatUserSubtitle(user)}
      onLogout={clearToken}
    >
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Devices error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-3">
        <Card className="rounded-3xl xl:col-span-2">
          <CardHeader>
            <CardTitle>Device list</CardTitle>
            <CardDescription>
              Heartbeat status, firmware, and last-seen details for current boards.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DevicesTable devices={devices} />
          </CardContent>
        </Card>

        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle>Summary</CardTitle>
            <CardDescription>Current device and entity counts.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <div>devices: {devices.length}</div>
            <div>online: {devices.filter((device) => device.status === "online").length}</div>
            <div>entities: {entities.length}</div>
            <div>
              writable: {entities.filter((entity) => entity.writable === 1).length}
            </div>
          </CardContent>
        </Card>
      </section>

      <Card className="rounded-3xl">
        <CardHeader>
          <CardTitle>Entities</CardTitle>
          <CardDescription>
            Current state and direct control for writable entities.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <EntitiesTable
            entities={entities}
            states={states}
            busyEntityId={busyEntityId}
            onRelayCommand={(entityId, on) => void sendRelayCommand(entityId, on)}
          />
        </CardContent>
      </Card>
    </AppShell>
  );
}

