"use client";

import { useEffect, useEffectEvent, useMemo, useState } from "react";

import { AppShell } from "@/components/dashboard/app-shell";
import { AuditFeed } from "@/components/dashboard/audit-feed";
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
  buildDashboardWebSocketUrl,
  formatUserSubtitle,
  resolveApiBaseUrl,
  User,
} from "@/lib/alice-client";
import { useDashboardToken } from "@/hooks/use-dashboard-token";

export default function AuditPage() {
  const apiBaseUrl = useMemo(() => resolveApiBaseUrl(), []);
  const { token, tokenReady, clearToken } = useDashboardToken();

  const [user, setUser] = useState<User | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadAudit = useEffectEvent(async () => {
    if (!token) {
      return;
    }

    try {
      const [me, auditResponse] = await Promise.all([
        apiFetch<User>(apiBaseUrl, "/auth/me", token),
        apiFetch<{ items: AuditEvent[] }>(apiBaseUrl, "/audit-events?limit=50", token),
      ]);
      setUser(me);
      setAuditEvents(auditResponse.items);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to load audit");
    }
  });

  useEffect(() => {
    if (!tokenReady || !token) {
      return;
    }

    const timeout = window.setTimeout(() => void loadAudit(), 0);
    const interval = window.setInterval(() => void loadAudit(), 30000);
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
          void loadAudit();
        }
      } catch {
        void loadAudit();
      }
    };

    return () => websocket.close();
  }, [apiBaseUrl, token]);

  if (!tokenReady) {
    return null;
  }

  if (!token) {
    return <AuthRequiredCard description="Return to the dashboard and sign in before opening audit." />;
  }

  return (
    <AppShell
      title="Audit"
      description="Dedicated event stream page for state changes, commands, and acknowledgements."
      subtitle={formatUserSubtitle(user)}
      onLogout={clearToken}
    >
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Audit error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card className="rounded-3xl">
        <CardHeader>
          <CardTitle>Audit stream</CardTitle>
          <CardDescription>
            Latest projected events from Home OS.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AuditFeed events={auditEvents} emptyMessage="No recent audit events." />
        </CardContent>
      </Card>
    </AppShell>
  );
}

