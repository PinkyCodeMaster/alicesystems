import { router } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import {
  apiRequest,
  formatTimestamp,
  isUnauthorizedError,
  type Device,
  type Entity,
} from '@/lib/alice-api';
import { useDashboardLiveRefresh } from '@/hooks/use-dashboard-live-refresh';
import { getMobilePalette } from '@/lib/mobile-theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { useAliceSession } from '@/providers/alice-session';

type DeviceSummary = Device & {
  entityCount: number;
};

type DeviceSection = {
  title: string;
  description: string;
  items: DeviceSummary[];
};

export default function DevicesListScreen() {
  const { apiBaseUrl, authenticated, logout, token } = useAliceSession();
  const colorScheme = useColorScheme();
  const palette = getMobilePalette(colorScheme);

  const [devices, setDevices] = useState<Device[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(
    async (isPullToRefresh: boolean) => {
      if (!token) {
        return;
      }

      if (isPullToRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      try {
        const [deviceResponse, entityResponse] = await Promise.all([
          apiRequest<{ items: Device[] }>(apiBaseUrl, '/devices', undefined, token),
          apiRequest<{ items: Entity[] }>(apiBaseUrl, '/entities', undefined, token),
        ]);

        setDevices(deviceResponse.items);
        setEntities(entityResponse.items);
        setError(null);
      } catch (nextError) {
        if (isUnauthorizedError(nextError)) {
          logout();
        }
        setError(nextError instanceof Error ? nextError.message : 'Unable to load devices.');
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [apiBaseUrl, logout, token],
  );

  useEffect(() => {
    if (!authenticated || !token) {
      setDevices([]);
      setEntities([]);
      return;
    }

    void loadData(false);
  }, [authenticated, loadData, token]);

  useDashboardLiveRefresh({
    apiBaseUrl,
    token,
    enabled: authenticated,
    onInvalidate: () => {
      void loadData(false);
    },
  });

  const deviceSummaries = useMemo<DeviceSummary[]>(
    () =>
      devices
        .map((device) => ({
          ...device,
          entityCount: entities.filter((entity) => entity.device_id === device.id).length,
        }))
        .sort((left, right) => {
          if (left.status === right.status) {
            return left.name.localeCompare(right.name);
          }

          return left.status === 'online' ? -1 : 1;
        }),
    [devices, entities],
  );
  const deviceSections = useMemo<DeviceSection[]>(() => {
    const unplaced = deviceSummaries.filter((device) => !device.room_name);
    const byRoom = new Map<string, DeviceSummary[]>();

    for (const device of deviceSummaries) {
      if (!device.room_name) {
        continue;
      }
      const current = byRoom.get(device.room_name) ?? [];
      current.push(device);
      byRoom.set(device.room_name, current);
    }

    const sections: DeviceSection[] = [];
    if (unplaced.length > 0) {
      sections.push({
        title: 'Needs placement',
        description: 'Finish putting these devices into the right rooms.',
        items: unplaced,
      });
    }

    sections.push(
      ...Array.from(byRoom.entries())
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([roomName, items]) => ({
          title: roomName,
          description: `${items.filter((device) => device.status === 'online').length} online of ${items.length}`,
          items,
        })),
    );

    return sections;
  }, [deviceSummaries]);

  if (!authenticated) {
    return (
      <SafeAreaView style={[styles.safeArea, { backgroundColor: palette.background }]}>
        <View style={styles.emptyState}>
          <Text style={[styles.emptyTitle, { color: palette.text }]}>Sign in on Home</Text>
          <Text style={[styles.emptyBody, { color: palette.muted }]}>
            Devices become available after the Home OS login flow completes.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: palette.background }]}>
      <ScrollView
        contentContainerStyle={styles.screenContent}
        refreshControl={
          <RefreshControl
            onRefresh={() => void loadData(true)}
            refreshing={refreshing}
            tintColor={palette.primary}
          />
        }>
        <View style={[styles.headerCard, { backgroundColor: palette.hero }]}>
          <Text style={[styles.eyebrow, { color: palette.eyebrow }]}>Home devices</Text>
          <Text style={[styles.headerTitle, { color: palette.heroText }]}>Devices</Text>
          <Text style={[styles.headerBody, { color: palette.heroSubtle }]}>
            See what is active in each room, spot anything still unplaced, and open a device when
            you need detail or direct control.
          </Text>
        </View>

        {loading && devices.length === 0 ? (
          <ActivityIndicator color={palette.primary} style={styles.loader} />
        ) : null}

        {error ? (
          <View style={[styles.messageCard, { backgroundColor: palette.panel, borderColor: palette.border }]}>
            <Text style={[styles.errorText, { color: palette.danger }]}>{error}</Text>
          </View>
        ) : null}

        {deviceSummaries.length === 0 && !loading ? (
          <View style={[styles.messageCard, { backgroundColor: palette.panel, borderColor: palette.border }]}>
            <Text style={[styles.emptyTitle, { color: palette.text }]}>No devices yet</Text>
            <Text style={[styles.emptyBody, { color: palette.muted }]}>
              Open the Add tab to scan your first Alice device and place it in a room.
            </Text>
          </View>
        ) : null}

        {deviceSections.map((section) => (
          <View
            key={section.title}
            style={[styles.sectionCard, { backgroundColor: palette.panel, borderColor: palette.border }]}>
            <Text style={[styles.sectionTitle, { color: palette.text }]}>{section.title}</Text>
            <Text style={[styles.sectionBody, { color: palette.muted }]}>{section.description}</Text>

            {section.items.map((device) => (
              <Pressable
                key={device.id}
                onPress={() =>
                  router.push({
                    pathname: '/devices/[deviceId]',
                    params: { deviceId: device.id },
                  })
                }
                style={({ pressed }) => [
                  styles.deviceCard,
                  {
                    backgroundColor: palette.subtlePanel,
                    borderColor: palette.border,
                    opacity: pressed ? 0.92 : 1,
                  },
                ]}>
                <View style={styles.deviceHeader}>
                  <View style={styles.deviceHeaderCopy}>
                    <Text style={[styles.deviceName, { color: palette.text }]}>{device.name}</Text>
                    <Text style={[styles.deviceMeta, { color: palette.muted }]}>
                      {device.model} | {device.device_type}
                    </Text>
                    <Text style={[styles.deviceMeta, { color: palette.placeholder }]}>
                      {device.room_name ? `Room: ${device.room_name}` : 'Room: Not placed yet'}
                    </Text>
                  </View>
                  <View
                    style={[
                      styles.statusBadge,
                      {
                        backgroundColor:
                          device.status === 'online' ? palette.goodMuted : palette.warnMuted,
                      },
                    ]}>
                    <Text
                      style={[
                        styles.statusText,
                        {
                          color: device.status === 'online' ? palette.goodText : palette.warnText,
                        },
                      ]}>
                      {device.status}
                    </Text>
                  </View>
                </View>

                <View style={styles.metaRow}>
                  <Metric label="Capabilities" value={String(device.entityCount)} palette={palette} />
                  <Metric
                    label="Firmware"
                    value={device.fw_version ?? 'Unknown'}
                    palette={palette}
                  />
                </View>

                <Text style={[styles.lastSeenText, { color: palette.placeholder }]}>
                  Last seen {formatTimestamp(device.last_seen_at)}
                </Text>
                <Text style={[styles.openHint, { color: palette.primary }]}>Open detail</Text>
              </Pressable>
            ))}
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

function Metric({
  label,
  value,
  palette,
}: {
  label: string;
  value: string;
  palette: ReturnType<typeof getMobilePalette>;
}) {
  return (
    <View style={[styles.metricPill, { backgroundColor: palette.subtlePanel }]}>
      <Text style={[styles.metricLabel, { color: palette.muted }]}>{label}</Text>
      <Text style={[styles.metricValue, { color: palette.text }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
  screenContent: {
    padding: 20,
    gap: 16,
  },
  headerCard: {
    borderRadius: 28,
    gap: 8,
    padding: 22,
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1.4,
    textTransform: 'uppercase',
  },
  headerTitle: {
    fontSize: 30,
    fontWeight: '700',
  },
  headerBody: {
    fontSize: 15,
    lineHeight: 22,
  },
  loader: {
    paddingVertical: 24,
  },
  messageCard: {
    borderRadius: 22,
    borderWidth: 1,
    gap: 6,
    padding: 18,
  },
  sectionCard: {
    borderRadius: 24,
    borderWidth: 1,
    gap: 14,
    padding: 18,
  },
  sectionTitle: {
    fontSize: 22,
    fontWeight: '700',
  },
  sectionBody: {
    fontSize: 14,
    lineHeight: 20,
  },
  errorText: {
    fontSize: 14,
    lineHeight: 20,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
  },
  emptyTitle: {
    fontSize: 22,
    fontWeight: '700',
    marginBottom: 8,
  },
  emptyBody: {
    fontSize: 15,
    lineHeight: 22,
  },
  deviceCard: {
    borderRadius: 24,
    borderWidth: 1,
    gap: 14,
    padding: 18,
  },
  deviceHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'space-between',
  },
  deviceHeaderCopy: {
    flex: 1,
    gap: 4,
  },
  deviceName: {
    fontSize: 20,
    fontWeight: '700',
  },
  deviceMeta: {
    fontSize: 14,
    lineHeight: 20,
  },
  statusBadge: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.7,
    textTransform: 'uppercase',
  },
  metaRow: {
    flexDirection: 'row',
    gap: 10,
  },
  metricPill: {
    borderRadius: 18,
    flex: 1,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  metricLabel: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.7,
    marginBottom: 4,
    textTransform: 'uppercase',
  },
  metricValue: {
    fontSize: 15,
    fontWeight: '700',
  },
  lastSeenText: {
    fontSize: 12,
  },
  openHint: {
    fontSize: 13,
    fontWeight: '700',
  },
});
