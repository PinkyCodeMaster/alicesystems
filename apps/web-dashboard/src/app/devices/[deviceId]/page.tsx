"use client";

import { useParams } from "next/navigation";
import { useEffect, useEffectEvent, useMemo, useState } from "react";

import { AppShell } from "@/components/dashboard/app-shell";
import { AuditFeed } from "@/components/dashboard/audit-feed";
import { AuthRequiredCard } from "@/components/dashboard/auth-required-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
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
  DeviceDetail,
  formatDate,
  formatState,
  formatUserSubtitle,
  getStatusVariant,
  resolveApiBaseUrl,
  User,
} from "@/lib/alice-client";
import { useDashboardToken } from "@/hooks/use-dashboard-token";

export default function DeviceDetailPage() {
  const params = useParams<{ deviceId: string }>();
  const deviceId = params.deviceId;
  const apiBaseUrl = useMemo(() => resolveApiBaseUrl(), []);
  const { token, tokenReady, clearToken } = useDashboardToken();

  const [user, setUser] = useState<User | null>(null);
  const [detail, setDetail] = useState<DeviceDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadDetail = useEffectEvent(async () => {
    if (!token) {
      return;
    }

    try {
      const [me, nextDetail] = await Promise.all([
        apiFetch<User>(apiBaseUrl, "/auth/me", token),
        apiFetch<DeviceDetail>(apiBaseUrl, `/devices/${deviceId}`, token),
      ]);
      setUser(me);
      setDetail(nextDetail);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to load device");
    }
  });

  useEffect(() => {
    if (!tokenReady || !token) {
      return;
    }

    const timeout = window.setTimeout(() => void loadDetail(), 0);
    const interval = window.setInterval(() => void loadDetail(), 30000);
    return () => {
      window.clearTimeout(timeout);
      window.clearInterval(interval);
    };
  }, [tokenReady, token, apiBaseUrl, deviceId]);

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
          (!payload.target_id ||
            payload.target_id === deviceId ||
            detail?.entities.some((entity) => entity.id === payload.target_id))
        ) {
          void loadDetail();
        }
      } catch {
        void loadDetail();
      }
    };

    return () => websocket.close();
  }, [apiBaseUrl, token, deviceId, detail]);

  if (!tokenReady) {
    return null;
  }

  if (!token) {
    return (
      <AuthRequiredCard description="Return to the dashboard and sign in before opening device detail pages." />
    );
  }

  return (
    <AppShell
      title={detail?.device.name ?? "Device detail"}
      description={detail?.device.id ?? deviceId}
      subtitle={formatUserSubtitle(user)}
      onLogout={clearToken}
    >
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Device detail error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="rounded-2xl shadow-sm">
          <CardContent className="p-6">
            <p className="text-sm text-muted-foreground">Status</p>
            <div className="mt-2">
              <Badge variant={getStatusVariant(detail?.device.status ?? "offline")}>
                {detail?.device.status ?? "unknown"}
              </Badge>
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
            <p className="mt-1 text-sm font-medium">
              {formatDate(detail?.device.last_seen_at)}
            </p>
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
            {detail?.entities.map((entity) => (
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
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle>Recent audit</CardTitle>
            <CardDescription>
              Latest events for this device and its projected entities.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <AuditFeed
              events={detail?.audit_events ?? []}
              emptyMessage="No recent audit events."
            />
          </CardContent>
        </Card>
      </section>
    </AppShell>
  );
}

