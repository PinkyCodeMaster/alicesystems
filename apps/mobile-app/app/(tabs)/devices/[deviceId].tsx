import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import {
  apiRequest,
  createRoomRequest,
  deleteDeviceRequest,
  formatStateValue,
  formatTimestamp,
  isUnauthorizedError,
  parseMetadata,
  sendSwitchCommand,
  updateDeviceRequest,
  type DeviceDetail,
  type DeviceDetailEntity,
  type Room,
} from '@/lib/alice-api';
import { useDashboardLiveRefresh } from '@/hooks/use-dashboard-live-refresh';
import { getMobilePalette } from '@/lib/mobile-theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { useAliceSession } from '@/providers/alice-session';

export default function DeviceDetailScreen() {
  const { deviceId } = useLocalSearchParams<{ deviceId: string }>();
  const router = useRouter();
  const { apiBaseUrl, logout, token } = useAliceSession();
  const colorScheme = useColorScheme();
  const palette = getMobilePalette(colorScheme);

  const [detail, setDetail] = useState<DeviceDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingEntityId, setPendingEntityId] = useState<string | null>(null);
  const [removing, setRemoving] = useState(false);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [metadataName, setMetadataName] = useState('');
  const [metadataRoomId, setMetadataRoomId] = useState<string | null>(null);
  const [metadataDirty, setMetadataDirty] = useState(false);
  const [metadataStatus, setMetadataStatus] = useState<string | null>(null);
  const [savingMetadata, setSavingMetadata] = useState(false);
  const [newRoomName, setNewRoomName] = useState('');
  const [creatingRoom, setCreatingRoom] = useState(false);

  const loadDetail = useCallback(
    async (isPullToRefresh: boolean) => {
      if (!token || !deviceId) {
        return;
      }

      if (isPullToRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      try {
        const [response, roomsResponse] = await Promise.all([
          apiRequest<DeviceDetail>(
            apiBaseUrl,
            `/devices/${deviceId}`,
            undefined,
            token,
          ),
          apiRequest<{ items: Room[] }>(apiBaseUrl, '/rooms', undefined, token),
        ]);
        setDetail(response);
        setRooms(roomsResponse.items);
        if (!metadataDirty) {
          setMetadataName(response.device.name);
          setMetadataRoomId(response.device.room_id);
        }
        setError(null);
      } catch (nextError) {
        if (isUnauthorizedError(nextError)) {
          logout();
        }
        setError(nextError instanceof Error ? nextError.message : 'Unable to load device detail.');
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [apiBaseUrl, deviceId, logout, metadataDirty, token],
  );

  useEffect(() => {
    void loadDetail(false);
  }, [loadDetail]);

  useDashboardLiveRefresh({
    apiBaseUrl,
    token,
    enabled: Boolean(deviceId && token),
    onInvalidate: () => {
      void loadDetail(false);
    },
  });

  const relayEntities = useMemo(
    () => detail?.entities.filter((entity) => entity.writable === 1) ?? [],
    [detail],
  );
  const selectedRoomName = useMemo(
    () => rooms.find((room) => room.id === metadataRoomId)?.name ?? 'Not placed yet',
    [metadataRoomId, rooms],
  );

  async function handleToggle(entity: DeviceDetailEntity, nextState: boolean) {
    if (!token) {
      return;
    }

    setPendingEntityId(entity.id);
    try {
      await sendSwitchCommand(apiBaseUrl, token, entity.id, nextState);
      await loadDetail(false);
    } catch (nextError) {
      if (isUnauthorizedError(nextError)) {
        logout();
      }
      setError(nextError instanceof Error ? nextError.message : 'Command failed.');
    } finally {
      setPendingEntityId(null);
    }
  }

  async function handleRemoveDevice() {
    if (!token || !deviceId || !detail) {
      return;
    }

    setRemoving(true);
    try {
      await deleteDeviceRequest(apiBaseUrl, token, deviceId);
      router.replace('/(tabs)/devices');
    } catch (nextError) {
      if (isUnauthorizedError(nextError)) {
        logout();
      }
      setError(nextError instanceof Error ? nextError.message : 'Unable to remove device.');
    } finally {
      setRemoving(false);
    }
  }

  async function handleSaveMetadata() {
    if (!token || !deviceId || !detail || savingMetadata) {
      return;
    }

    setSavingMetadata(true);
    setMetadataStatus(null);

    try {
      await updateDeviceRequest(apiBaseUrl, token, deviceId, {
        name: metadataName,
        room_id: metadataRoomId,
      });
      setMetadataDirty(false);
      setMetadataStatus(`Saved ${metadataName.trim() || detail.device.name} in ${selectedRoomName}.`);
      await loadDetail(false);
    } catch (nextError) {
      if (isUnauthorizedError(nextError)) {
        logout();
      }
      setError(nextError instanceof Error ? nextError.message : 'Unable to save device details.');
    } finally {
      setSavingMetadata(false);
    }
  }

  async function handleCreateRoom() {
    if (!token || creatingRoom || !newRoomName.trim()) {
      return;
    }

    setCreatingRoom(true);
    setMetadataStatus(null);

    try {
      const room = await createRoomRequest(apiBaseUrl, token, newRoomName);
      setRooms((current) => {
        const next = current.some((item) => item.id === room.id)
          ? current.map((item) => (item.id === room.id ? room : item))
          : [...current, room];
        return [...next].sort((left, right) => left.name.localeCompare(right.name));
      });
      setMetadataRoomId(room.id);
      setMetadataDirty(true);
      setNewRoomName('');
      setMetadataStatus(`Added ${room.name}. Save details to place this device there.`);
      setError(null);
    } catch (nextError) {
      if (isUnauthorizedError(nextError)) {
        logout();
      }
      setError(nextError instanceof Error ? nextError.message : 'Unable to create room.');
    } finally {
      setCreatingRoom(false);
    }
  }

  function confirmRemoveDevice() {
    if (!detail || removing) {
      return;
    }

    Alert.alert(
      'Remove device?',
      `Remove ${detail.device.name} from this hub and clear its current claim state?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: () => void handleRemoveDevice(),
        },
      ],
    );
  }

  if (!deviceId) {
    return (
      <SafeAreaView style={[styles.safeArea, { backgroundColor: palette.background }]}>
        <View style={styles.messageBlock}>
          <Text style={[styles.messageTitle, { color: palette.text }]}>Missing device ID</Text>
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
            onRefresh={() => void loadDetail(true)}
            refreshing={refreshing}
            tintColor={palette.primary}
          />
        }>
        {loading && !detail ? <ActivityIndicator color={palette.primary} style={styles.loader} /> : null}

        {error ? (
          <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
            <Text style={[styles.errorText, { color: palette.danger }]}>{error}</Text>
          </View>
        ) : null}

        {detail ? (
          <>
            <View style={[styles.heroCard, { backgroundColor: palette.hero }]}>
              <Text style={[styles.eyebrow, { color: palette.eyebrow }]}>Device detail</Text>
              <Text style={[styles.heroTitle, { color: palette.heroText }]}>{detail.device.name}</Text>
              <Text style={[styles.heroBody, { color: palette.heroSubtle }]}>
                {detail.device.model} | {detail.device.device_type} | {detail.device.protocol}
              </Text>
            </View>

            <View style={styles.metricRow}>
              <MetricCard
                label="Status"
                value={detail.device.status}
                tone={detail.device.status === 'online' ? 'good' : 'warning'}
                palette={palette}
              />
              <MetricCard
                label="Capabilities"
                value={String(detail.entities.length)}
                tone="neutral"
                palette={palette}
              />
              <MetricCard
                label="Firmware"
                value={detail.device.fw_version ?? 'Unknown'}
                tone="neutral"
                palette={palette}
              />
            </View>

            <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
              <Text style={[styles.panelTitle, { color: palette.text }]}>Summary</Text>
              <Text style={[styles.detailLine, { color: palette.muted }]}>ID: {detail.device.id}</Text>
              <Text style={[styles.detailLine, { color: palette.muted }]}>
                Provisioning: {detail.device.provisioning_status}
              </Text>
              <Text style={[styles.detailLine, { color: palette.muted }]}>
                Room: {detail.device.room_name ?? 'Not placed yet'}
              </Text>
              <Text style={[styles.detailLine, { color: palette.muted }]}>
                MQTT client: {detail.device.mqtt_client_id}
              </Text>
              <Text style={[styles.detailLine, { color: palette.muted }]}>
                Last seen: {formatTimestamp(detail.device.last_seen_at)}
              </Text>
            </View>

            <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
              <Text style={[styles.panelTitle, { color: palette.text }]}>Name and room</Text>
              <Text style={[styles.detailLine, { color: palette.muted }]}>
                Keep this device placed correctly across Alice.
              </Text>

              <View style={styles.fieldGroup}>
                <Text style={[styles.fieldLabel, { color: palette.muted }]}>Device name</Text>
                <TextInput
                  autoCapitalize="words"
                  autoCorrect={false}
                  onChangeText={(value) => {
                    setMetadataName(value);
                    setMetadataDirty(true);
                    setMetadataStatus(null);
                  }}
                  placeholder="Hall Sensor"
                  placeholderTextColor={palette.placeholder}
                  style={[
                    styles.input,
                    { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
                  ]}
                  value={metadataName}
                />
              </View>

              <View style={styles.fieldGroup}>
                <Text style={[styles.fieldLabel, { color: palette.muted }]}>Room</Text>
                <Text style={[styles.detailLine, { color: palette.muted }]}>
                  Current placement: {detail.device.room_name ?? 'Not placed yet'}
                </Text>
                <View style={styles.roomRow}>
                  <RoomChip
                    active={metadataRoomId === null}
                    label="No room yet"
                    onPress={() => {
                      setMetadataRoomId(null);
                      setMetadataDirty(true);
                      setMetadataStatus(null);
                    }}
                    palette={palette}
                  />
                  {rooms.map((room) => (
                    <RoomChip
                      key={room.id}
                      active={metadataRoomId === room.id}
                      label={room.name}
                      onPress={() => {
                        setMetadataRoomId(room.id);
                        setMetadataDirty(true);
                        setMetadataStatus(null);
                      }}
                      palette={palette}
                    />
                  ))}
                </View>
              </View>

              <View
                style={[
                  styles.entityCard,
                  { backgroundColor: palette.subtlePanel, borderColor: palette.border, gap: 10 },
                ]}>
                <Text style={[styles.fieldLabel, { color: palette.muted }]}>Add room</Text>
                <Text style={[styles.detailLine, { color: palette.muted }]}>
                  Create the missing room here instead of leaving this device unplaced.
                </Text>
                <TextInput
                  autoCapitalize="words"
                  autoCorrect={false}
                  onChangeText={(value) => {
                    setNewRoomName(value);
                    setMetadataStatus(null);
                  }}
                  placeholder="Utility Room"
                  placeholderTextColor={palette.placeholder}
                  style={[
                    styles.input,
                    { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
                  ]}
                  value={newRoomName}
                />
                <Pressable
                  disabled={creatingRoom || !newRoomName.trim()}
                  onPress={() => void handleCreateRoom()}
                  style={[
                    styles.secondaryButton,
                    { borderColor: palette.border, backgroundColor: palette.subtlePanel },
                    (creatingRoom || !newRoomName.trim()) ? styles.disabledButton : null,
                  ]}>
                  <Text style={[styles.secondaryButtonText, { color: palette.text }]}>
                    {creatingRoom ? 'Adding room...' : 'Add room'}
                  </Text>
                </Pressable>
              </View>

              {metadataStatus ? (
                <Text style={[styles.successText, { color: palette.goodText }]}>{metadataStatus}</Text>
              ) : null}

              <Pressable
                disabled={savingMetadata || !metadataDirty || !metadataName.trim()}
                onPress={() => void handleSaveMetadata()}
                style={[
                  styles.primaryButton,
                  { backgroundColor: palette.primary },
                  (savingMetadata || !metadataDirty || !metadataName.trim()) ? styles.disabledButton : null,
                ]}>
                <Text style={[styles.primaryButtonText, { color: palette.primaryText }]}>
                  {savingMetadata ? 'Saving...' : 'Save details'}
                </Text>
              </Pressable>
            </View>

            <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
              <Text style={[styles.panelTitle, { color: palette.text }]}>Controls</Text>
              {relayEntities.length === 0 ? (
                <Text style={[styles.detailLine, { color: palette.muted }]}>
                  No writable capabilities projected for this device yet.
                </Text>
              ) : (
                relayEntities.map((entity) => {
                  const currentOn =
                    typeof entity.state?.on === 'boolean' ? Boolean(entity.state.on) : null;
                  const nextState = currentOn === null ? true : !currentOn;

                  return (
                    <View
                      key={entity.id}
                      style={[
                        styles.entityCard,
                        { backgroundColor: palette.subtlePanel, borderColor: palette.border },
                      ]}>
                      <View style={styles.entityHeader}>
                        <View style={styles.entityCopy}>
                          <Text style={[styles.entityTitle, { color: palette.text }]}>{entity.name}</Text>
                          <Text style={[styles.entityMeta, { color: palette.placeholder }]}>
                            {entity.kind} | {entity.capability_id}
                          </Text>
                        </View>
                        <Pressable
                          disabled={pendingEntityId === entity.id || currentOn === null}
                          onPress={() => void handleToggle(entity, nextState)}
                          style={[
                            styles.commandButton,
                            { backgroundColor: currentOn ? palette.warnMuted : palette.goodMuted },
                            (pendingEntityId === entity.id || currentOn === null) && styles.disabledButton,
                          ]}>
                          <Text
                            style={[
                              styles.commandText,
                              { color: currentOn ? palette.warnText : palette.goodText },
                            ]}>
                            {pendingEntityId === entity.id
                              ? 'Sending...'
                              : currentOn === null
                                ? 'Unavailable'
                                : currentOn
                                  ? 'Turn off'
                                  : 'Turn on'}
                          </Text>
                        </Pressable>
                      </View>
                      <Text style={[styles.entityBody, { color: palette.muted }]}>
                        {formatStateValue(entity.state)}
                      </Text>
                    </View>
                  );
                })
              )}
            </View>

            <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
              <Text style={[styles.panelTitle, { color: palette.text }]}>Projected entities</Text>
              {detail.entities.map((entity) => (
                <View
                  key={entity.id}
                  style={[
                    styles.entityCard,
                    { backgroundColor: palette.subtlePanel, borderColor: palette.border },
                  ]}>
                  <Text style={[styles.entityTitle, { color: palette.text }]}>{entity.name}</Text>
                  <Text style={[styles.entityMeta, { color: palette.placeholder }]}>
                    {entity.kind} | {entity.capability_id}
                  </Text>
                  <Text style={[styles.entityBody, { color: palette.muted }]}>
                    {formatStateValue(entity.state)}
                  </Text>
                  <Text style={[styles.entityMeta, { color: palette.placeholder }]}>
                    Updated {formatTimestamp(entity.state_updated_at)}
                  </Text>
                </View>
              ))}
            </View>

            <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
              <Text style={[styles.panelTitle, { color: palette.text }]}>Recent audit</Text>
              {detail.audit_events.length === 0 ? (
                <Text style={[styles.detailLine, { color: palette.muted }]}>No recent audit events.</Text>
              ) : (
                detail.audit_events.slice(0, 6).map((event) => {
                  const metadata = parseMetadata(event.metadata_json);

                  return (
                    <View
                      key={event.id}
                      style={[
                        styles.auditCard,
                        { backgroundColor: palette.subtlePanel, borderColor: palette.border },
                      ]}>
                      <Text style={[styles.auditAction, { color: palette.text }]}>{event.action}</Text>
                      <Text style={[styles.entityMeta, { color: palette.placeholder }]}>
                        {event.target_type} | {event.severity}
                      </Text>
                      <Text style={[styles.auditBody, { color: palette.muted }]}>
                        {String(metadata.command ?? metadata.status ?? event.target_id ?? 'No extra metadata')}
                      </Text>
                      <Text style={[styles.entityMeta, { color: palette.placeholder }]}>
                        {formatTimestamp(event.created_at)}
                      </Text>
                    </View>
                  );
                })
              )}
            </View>

            <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
              <Text style={[styles.panelTitle, { color: palette.text }]}>Danger zone</Text>
              <Text style={[styles.detailLine, { color: palette.muted }]}>
                Remove this device from the hub so it no longer appears in Home OS. Claimed bootstrap
                records are reset so this device can be adopted again later.
              </Text>
              <Pressable
                disabled={removing}
                onPress={confirmRemoveDevice}
                style={[
                  styles.removeButton,
                  { backgroundColor: '#FDECEC', borderColor: palette.danger },
                  removing ? styles.disabledButton : null,
                ]}>
                <Text style={[styles.removeButtonText, { color: palette.danger }]}>
                  {removing ? 'Removing...' : 'Remove device'}
                </Text>
              </Pressable>
            </View>
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function MetricCard({
  label,
  value,
  tone,
  palette,
}: {
  label: string;
  value: string;
  tone: 'good' | 'warning' | 'neutral';
  palette: ReturnType<typeof getMobilePalette>;
}) {
  const backgroundColor =
    tone === 'good' ? palette.goodMuted : tone === 'warning' ? palette.warnMuted : palette.subtlePanel;
  const textColor =
    tone === 'good' ? palette.goodText : tone === 'warning' ? palette.warnText : palette.text;

  return (
    <View style={[styles.metricCard, { backgroundColor }]}>
      <Text style={[styles.metricLabel, { color: palette.muted }]}>{label}</Text>
      <Text style={[styles.metricValue, { color: textColor }]} numberOfLines={1}>
        {value}
      </Text>
    </View>
  );
}

function RoomChip({
  active,
  label,
  onPress,
  palette,
}: {
  active: boolean;
  label: string;
  onPress: () => void;
  palette: ReturnType<typeof getMobilePalette>;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={[
        styles.roomChip,
        {
          backgroundColor: active ? palette.primary : palette.subtlePanel,
          borderColor: active ? palette.primary : palette.border,
        },
      ]}>
      <Text style={{ color: active ? palette.primaryText : palette.text, fontWeight: '700' }}>
        {label}
      </Text>
    </Pressable>
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
  loader: {
    paddingVertical: 24,
  },
  messageBlock: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
  },
  messageTitle: {
    fontSize: 22,
    fontWeight: '700',
  },
  heroCard: {
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
  heroTitle: {
    fontSize: 30,
    fontWeight: '700',
  },
  heroBody: {
    fontSize: 15,
    lineHeight: 22,
  },
  metricRow: {
    flexDirection: 'row',
    gap: 10,
  },
  metricCard: {
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
  panel: {
    borderRadius: 24,
    borderWidth: 1,
    gap: 12,
    padding: 18,
  },
  panelTitle: {
    fontSize: 20,
    fontWeight: '700',
  },
  fieldGroup: {
    gap: 8,
  },
  fieldLabel: {
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.3,
    textTransform: 'uppercase',
  },
  input: {
    borderRadius: 18,
    borderWidth: 1,
    fontSize: 16,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  roomRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    paddingVertical: 2,
  },
  roomChip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  errorText: {
    fontSize: 14,
    lineHeight: 20,
  },
  successText: {
    fontSize: 14,
    lineHeight: 20,
  },
  detailLine: {
    fontSize: 14,
    lineHeight: 20,
  },
  entityCard: {
    borderRadius: 18,
    borderWidth: 1,
    gap: 8,
    padding: 14,
  },
  entityHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'space-between',
  },
  entityCopy: {
    flex: 1,
    gap: 4,
  },
  entityTitle: {
    fontSize: 15,
    fontWeight: '700',
  },
  entityMeta: {
    fontSize: 12,
  },
  entityBody: {
    fontSize: 14,
    lineHeight: 20,
  },
  commandButton: {
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  commandText: {
    fontSize: 13,
    fontWeight: '700',
  },
  disabledButton: {
    opacity: 0.65,
  },
  primaryButton: {
    alignItems: 'center',
    borderRadius: 18,
    justifyContent: 'center',
    minHeight: 54,
    paddingHorizontal: 18,
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: '700',
  },
  secondaryButton: {
    alignItems: 'center',
    borderRadius: 18,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 54,
    paddingHorizontal: 18,
  },
  secondaryButtonText: {
    fontSize: 15,
    fontWeight: '700',
  },
  auditCard: {
    borderRadius: 18,
    borderWidth: 1,
    gap: 6,
    padding: 14,
  },
  auditAction: {
    fontSize: 15,
    fontWeight: '700',
  },
  auditBody: {
    fontSize: 14,
    lineHeight: 20,
  },
  removeButton: {
    alignItems: 'center',
    borderRadius: 18,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 54,
    paddingHorizontal: 18,
  },
  removeButtonText: {
    fontSize: 15,
    fontWeight: '700',
  },
});
