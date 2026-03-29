"use client";

import { FormEvent, useEffect, useEffectEvent, useMemo, useState } from "react";

import { AppShell } from "@/components/dashboard/app-shell";
import { AuditFeed } from "@/components/dashboard/audit-feed";
import { AuthRequiredCard } from "@/components/dashboard/auth-required-card";
import { AutoLightForm } from "@/components/dashboard/auto-light-form";
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
  authenticateDashboardWebSocket,
  AuditEvent,
  AutoLightSettings,
  buildDashboardWebSocketUrl,
  Entity,
  formatUserSubtitle,
  resolveApiBaseUrl,
  User,
} from "@/lib/alice-client";
import { useDashboardToken } from "@/hooks/use-dashboard-token";

export default function AutoLightPage() {
  const apiBaseUrl = useMemo(() => resolveApiBaseUrl(), []);
  const { token, tokenReady, clearToken } = useDashboardToken();

  const [user, setUser] = useState<User | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [autoLight, setAutoLight] = useState<AutoLightSettings | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadAutomation = async () => {
    if (!token) {
      return;
    }

    try {
      const [me, entityResponse, autoLightResponse, auditResponse] = await Promise.all([
        apiFetch<User>(apiBaseUrl, "/auth/me", token),
        apiFetch<{ items: Entity[] }>(apiBaseUrl, "/entities", token),
        apiFetch<AutoLightSettings>(apiBaseUrl, "/system/auto-light", token),
        apiFetch<{ items: AuditEvent[] }>(apiBaseUrl, "/audit-events?limit=20", token),
      ]);

      setUser(me);
      setEntities(entityResponse.items);
      setAutoLight(autoLightResponse);
      setAuditEvents(
        auditResponse.items.filter(
          (event) =>
            event.actor_id === "system:auto-light" ||
            event.target_id === autoLightResponse.target_entity_id ||
            event.target_id === autoLightResponse.sensor_entity_id,
        ),
      );
      setError(null);
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Failed to load auto-light settings",
      );
    }
  };
  const refreshAutomation = useEffectEvent(() => void loadAutomation());

  useEffect(() => {
    if (!tokenReady || !token) {
      return;
    }

    const timeout = window.setTimeout(() => void refreshAutomation(), 0);
    const interval = window.setInterval(() => void refreshAutomation(), 30000);
    return () => {
      window.clearTimeout(timeout);
      window.clearInterval(interval);
    };
  }, [tokenReady, token, apiBaseUrl]);

  useEffect(() => {
    if (!token) {
      return;
    }

    const websocket = new WebSocket(buildDashboardWebSocketUrl(apiBaseUrl));
    websocket.onopen = () => authenticateDashboardWebSocket(websocket, token);
    websocket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type?: string };
        if (payload.type && payload.type !== "ping" && payload.type !== "connected") {
          void refreshAutomation();
        }
      } catch {
        void refreshAutomation();
      }
    };

    return () => websocket.close();
  }, [apiBaseUrl, token]);

  const saveAutoLight = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !autoLight) return;

    setSaving(true);
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
      setError(null);
      await loadAutomation();
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "Failed to save auto-light",
      );
    } finally {
      setSaving(false);
    }
  };

  if (!tokenReady) {
    return null;
  }

  if (!token) {
    return <AuthRequiredCard description="Return to Alice Web and sign in before opening automations." />;
  }

  return (
    <AppShell
      title="Auto-light"
      description="Compartmentalized automation editing for thresholds, mode, and entity mapping."
      subtitle={formatUserSubtitle(user)}
      onLogout={clearToken}
    >
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Automation error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.9fr)]">
        {autoLight ? (
          <AutoLightForm
            autoLight={autoLight}
            entities={entities}
            saving={saving}
            onSubmit={saveAutoLight}
            onChange={setAutoLight}
          />
        ) : null}

        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle>Automation audit</CardTitle>
            <CardDescription>
              Recent audit entries related to the current auto-light automation.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <AuditFeed
              events={auditEvents}
              emptyMessage="No recent auto-light audit events."
            />
          </CardContent>
        </Card>
      </section>
    </AppShell>
  );
}

