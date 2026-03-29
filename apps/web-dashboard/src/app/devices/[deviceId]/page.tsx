"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/dashboard/app-shell";
import { AuditFeed } from "@/components/dashboard/audit-feed";
import { AuthRequiredCard } from "@/components/dashboard/auth-required-card";
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
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import {
  apiFetch,
  authenticateDashboardWebSocket,
  buildDashboardWebSocketUrl,
  createRoomRequest,
  deleteDeviceRequest,
  DeviceDetail,
  formatDate,
  formatState,
  formatUserSubtitle,
  getStatusVariant,
  Room,
  resolveApiBaseUrl,
  updateDeviceRequest,
  User,
} from "@/lib/alice-client";
import { useDashboardToken } from "@/hooks/use-dashboard-token";

export default function DeviceDetailPage() {
  const params = useParams<{ deviceId: string }>();
  const router = useRouter();
  const deviceId = params.deviceId;
  const apiBaseUrl = useMemo(() => resolveApiBaseUrl(), []);
  const { token, tokenReady, clearToken } = useDashboardToken();

  const [user, setUser] = useState<User | null>(null);
  const [detail, setDetail] = useState<DeviceDetail | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [removing, setRemoving] = useState(false);
  const [savingMetadata, setSavingMetadata] = useState(false);
  const [metadataName, setMetadataName] = useState("");
  const [metadataRoomId, setMetadataRoomId] = useState("");
  const [metadataDirty, setMetadataDirty] = useState(false);
  const [metadataStatus, setMetadataStatus] = useState<string | null>(null);
  const [newRoomName, setNewRoomName] = useState("");
  const [creatingRoom, setCreatingRoom] = useState(false);
  const hasRelayEntity = useMemo(
    () => detail?.entities.some((entity) => entity.kind === "switch.relay" && entity.writable === 1) ?? false,
    [detail],
  );
  const hasAutomationSensor = useMemo(
    () =>
      detail?.entities.some(
        (entity) => entity.kind === "sensor.motion" || entity.kind === "sensor.illuminance",
      ) ?? false,
    [detail],
  );

  const loadDetail = useCallback(async () => {
    if (!token) {
      return;
    }

    try {
      const [me, nextDetail, roomsResponse] = await Promise.all([
        apiFetch<User>(apiBaseUrl, "/auth/me", token),
        apiFetch<DeviceDetail>(apiBaseUrl, `/devices/${deviceId}`, token),
        apiFetch<{ items: Room[] }>(apiBaseUrl, "/rooms", token),
      ]);
      setUser(me);
      setDetail(nextDetail);
      setRooms(roomsResponse.items);
      if (!metadataDirty) {
        setMetadataName(nextDetail.device.name);
        setMetadataRoomId(nextDetail.device.room_id ?? "");
      }
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to load device");
    }
  }, [apiBaseUrl, deviceId, metadataDirty, token]);

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
  }, [tokenReady, token, loadDetail]);

  useEffect(() => {
    if (!token) {
      return;
    }

    const websocket = new WebSocket(buildDashboardWebSocketUrl(apiBaseUrl));
    websocket.onopen = () => authenticateDashboardWebSocket(websocket, token);
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
  }, [apiBaseUrl, detail, deviceId, loadDetail, token]);

  const handleSaveMetadata = async () => {
    if (!token || !detail || savingMetadata) {
      return;
    }

    setSavingMetadata(true);
    setMetadataStatus(null);
    try {
      await updateDeviceRequest(apiBaseUrl, deviceId, token, {
        name: metadataName,
        room_id: metadataRoomId || null,
      });
      setMetadataDirty(false);
      setMetadataStatus("Saved device name and room.");
      await loadDetail();
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to save device details");
    } finally {
      setSavingMetadata(false);
    }
  };

  const handleCreateRoom = async () => {
    if (!token || creatingRoom || !newRoomName.trim()) {
      return;
    }

    setCreatingRoom(true);
    setMetadataStatus(null);
    try {
      const room = await createRoomRequest(apiBaseUrl, token, newRoomName);
      setRooms((current) =>
        [...current.filter((item) => item.id !== room.id), room].sort((left, right) =>
          left.name.localeCompare(right.name),
        ),
      );
      setMetadataRoomId(room.id);
      setMetadataDirty(true);
      setNewRoomName("");
      setMetadataStatus(`Added ${room.name}. Save details to place this device there.`);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to add room");
    } finally {
      setCreatingRoom(false);
    }
  };

  const handleRemoveDevice = async () => {
    if (!token || !detail || removing) {
      return;
    }

    const confirmed = window.confirm(
      `Remove ${detail.device.name}? This deletes the device record and its projected entities.`,
    );
    if (!confirmed) {
      return;
    }

    setRemoving(true);
    try {
      await deleteDeviceRequest(apiBaseUrl, deviceId, token);
      setError(null);
      router.replace("/devices");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to remove device");
    } finally {
      setRemoving(false);
    }
  };

  if (!tokenReady) {
    return null;
  }

  if (!token) {
    return (
      <AuthRequiredCard description="Return to Alice Web and sign in before opening device detail pages." />
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
            <p className="text-sm text-muted-foreground">Room</p>
            <p className="mt-1 text-lg font-medium">
              {detail?.device.room_name ?? "Not placed yet"}
            </p>
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

        <div className="space-y-6">
          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle>Name and room</CardTitle>
              <CardDescription>
                Keep this device placed and labeled correctly across Alice surfaces.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <label className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                  Device name
                </label>
                <Input
                  value={metadataName}
                  onChange={(event) => {
                    setMetadataName(event.target.value);
                    setMetadataDirty(true);
                    setMetadataStatus(null);
                  }}
                  placeholder="Hall Sensor"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                  Room
                </label>
                <NativeSelect
                  className="w-full"
                  value={metadataRoomId}
                  onChange={(event) => {
                    setMetadataRoomId(event.target.value);
                    setMetadataDirty(true);
                    setMetadataStatus(null);
                  }}
                >
                  <NativeSelectOption value="">No room yet</NativeSelectOption>
                  {rooms.map((room) => (
                    <NativeSelectOption key={room.id} value={room.id}>
                      {room.name}
                    </NativeSelectOption>
                  ))}
                </NativeSelect>
                <p className="text-sm text-muted-foreground">
                  Current placement: {detail?.device.room_name ?? "Not placed yet"}
                </p>
              </div>
              <div className="space-y-2 rounded-2xl border border-dashed border-border/70 bg-muted/30 p-4">
                <label className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                  Add room
                </label>
                <p className="text-sm text-muted-foreground">
                  Create the missing room here instead of leaving this device unplaced.
                </p>
                <div className="flex gap-3">
                  <Input
                    value={newRoomName}
                    onChange={(event) => {
                      setNewRoomName(event.target.value);
                      setMetadataStatus(null);
                    }}
                    placeholder="Utility Room"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    disabled={creatingRoom || !newRoomName.trim()}
                    onClick={() => void handleCreateRoom()}
                  >
                    {creatingRoom ? "Adding..." : "Add room"}
                  </Button>
                </div>
              </div>
              {metadataStatus ? (
                <p className="text-sm text-emerald-700">{metadataStatus}</p>
              ) : null}
              <Button
                size="lg"
                disabled={!detail || savingMetadata || !metadataDirty}
                onClick={() => void handleSaveMetadata()}
              >
                {savingMetadata ? "Saving..." : "Save details"}
              </Button>
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

          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle>Suggested next step</CardTitle>
              <CardDescription>
                Keep the admin surface focused on the next real configuration step.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                {hasAutomationSensor
                  ? "This device already exposes motion or light data. Use Auto Light to wire it into a real room behavior."
                  : hasRelayEntity
                    ? "This device is ready for direct control. Verify command flow from the device list or through Alice Assistant."
                    : "Review projected entities and recent audit to confirm this device settled in cleanly."}
              </p>
              <Button
                variant="outline"
                size="lg"
                onClick={() => router.push(hasAutomationSensor ? "/automations/auto-light" : "/devices")}
              >
                {hasAutomationSensor ? "Open Auto Light" : "Open devices list"}
              </Button>
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-destructive/30">
            <CardHeader>
              <CardTitle>Remove device</CardTitle>
              <CardDescription>
                Remove this device from the hub so it can be claimed again cleanly.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                This deletes the device record, projected entities, and stored device
                credentials.
              </p>
              <Button
                variant="destructive"
                size="lg"
                disabled={!detail || removing}
                onClick={() => void handleRemoveDevice()}
              >
                {removing ? "Removing..." : "Remove device"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>
    </AppShell>
  );
}

