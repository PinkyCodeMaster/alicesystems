import { useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
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
  completeHubSetupRequest,
  formatStateValue,
  formatTimestamp,
  isUnauthorizedError,
  type Device,
  type Entity,
  type EntityState,
  type HubSetupStatus,
  type RootResponse,
  type StackHealth,
} from '@/lib/alice-api';
import { useDashboardLiveRefresh } from '@/hooks/use-dashboard-live-refresh';
import { getMobilePalette } from '@/lib/mobile-theme';
import { useAliceSession } from '@/providers/alice-session';
import { useColorScheme } from '@/hooks/use-color-scheme';

type OverviewState = {
  site: RootResponse | null;
  devices: Device[];
  entities: Entity[];
  states: EntityState[];
  stackHealth: StackHealth | null;
};

const EMPTY_OVERVIEW: OverviewState = {
  site: null,
  devices: [],
  entities: [],
  states: [],
  stackHealth: null,
};

const DEFAULT_ROOM_NAMES =
  'Living Room, Kitchen, Dining Room, Downstairs Bathroom, Upstairs Bathroom, Master Bedroom, Kids Room';

export default function OverviewScreen() {
  const router = useRouter();
  const { apiBaseUrl, authenticated, hydrateSession, login, logout, token, user } = useAliceSession();
  const colorScheme = useColorScheme();
  const palette = getMobilePalette(colorScheme);

  const [apiBaseUrlInput, setApiBaseUrlInput] = useState(apiBaseUrl);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [setupStatus, setSetupStatus] = useState<HubSetupStatus | null>(null);
  const [setupLoading, setSetupLoading] = useState(false);
  const [setupSiteName, setSetupSiteName] = useState('Alice Home');
  const [setupTimezone, setSetupTimezone] = useState('Europe/London');
  const [setupOwnerName, setSetupOwnerName] = useState('');
  const [setupOwnerEmail, setSetupOwnerEmail] = useState('');
  const [setupPassword, setSetupPassword] = useState('');
  const [setupPasswordConfirm, setSetupPasswordConfirm] = useState('');
  const [setupRoomNames, setSetupRoomNames] = useState(DEFAULT_ROOM_NAMES);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [isSettingUp, setIsSettingUp] = useState(false);

  const [overview, setOverview] = useState<OverviewState>(EMPTY_OVERVIEW);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    setApiBaseUrlInput(apiBaseUrl);
  }, [apiBaseUrl]);

  const loadSetupStatus = useCallback(async () => {
    setSetupLoading(true);
    try {
      const status = await apiRequest<HubSetupStatus>(apiBaseUrlInput, '/system/setup-status');
      setSetupStatus(status);
      setSetupSiteName(status.site_name || 'Alice Home');
      setSetupTimezone(status.timezone || 'Europe/London');
      if (!status.requires_onboarding) {
        setSetupError(null);
      }
    } catch (error) {
      setSetupStatus(null);
      setSetupError(error instanceof Error ? error.message : 'Unable to load hub setup state.');
    } finally {
      setSetupLoading(false);
    }
  }, [apiBaseUrlInput]);

  useEffect(() => {
    if (authenticated) {
      return;
    }
    void loadSetupStatus();
  }, [authenticated, loadSetupStatus]);

  const loadOverview = useCallback(
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
        const [site, devices, entities, states, stackHealth] = await Promise.all([
          apiRequest<RootResponse>(apiBaseUrl, '/', undefined, token),
          apiRequest<{ items: Device[] }>(apiBaseUrl, '/devices', undefined, token),
          apiRequest<{ items: Entity[] }>(apiBaseUrl, '/entities', undefined, token),
          apiRequest<{ items: EntityState[] }>(apiBaseUrl, '/entities/states', undefined, token),
          apiRequest<StackHealth>(apiBaseUrl, '/system/stack-health', undefined, token),
        ]);

        setOverview({
          site,
          devices: devices.items,
          entities: entities.items,
          states: states.items,
          stackHealth,
        });
        setLoadError(null);
      } catch (error) {
        if (isUnauthorizedError(error)) {
          logout();
        }
        setLoadError(error instanceof Error ? error.message : 'Unable to load Home OS data.');
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [apiBaseUrl, logout, token],
  );

  useEffect(() => {
    if (!authenticated || !token) {
      setOverview(EMPTY_OVERVIEW);
      return;
    }

    void loadOverview(false);
  }, [authenticated, loadOverview, token]);

  useDashboardLiveRefresh({
    apiBaseUrl,
    token,
    enabled: authenticated,
    onInvalidate: () => {
      void loadOverview(false);
    },
  });

  async function handleLogin() {
    setIsLoggingIn(true);
    setLoginError(null);

    try {
      await login({
        apiBaseUrl: apiBaseUrlInput,
        email,
        password,
      });
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'Login failed.');
    } finally {
      setIsLoggingIn(false);
    }
  }

  async function handleSetup() {
    if (setupPassword !== setupPasswordConfirm) {
      setSetupError('Passwords do not match.');
      return;
    }

    setIsSettingUp(true);
    setSetupError(null);
    try {
      const response = await completeHubSetupRequest(apiBaseUrlInput, {
        siteName: setupSiteName,
        timezone: setupTimezone,
        ownerEmail: setupOwnerEmail,
        ownerDisplayName: setupOwnerName,
        password: setupPassword,
        roomNames: setupRoomNames
          .split(',')
          .map((name) => name.trim())
          .filter(Boolean),
      });
      await hydrateSession(apiBaseUrlInput, response.access_token);
    } catch (error) {
      setSetupError(error instanceof Error ? error.message : 'Hub setup failed.');
    } finally {
      setIsSettingUp(false);
    }
  }

  const onlineDevices = overview.stackHealth?.devices.online ?? overview.devices.filter((device) => device.status === 'online').length;
  const placedDevices = overview.devices.filter((device) => device.room_name);
  const unplacedDevices = overview.devices.filter((device) => !device.room_name);
  const roomSummaries = useMemo(
    () =>
      Object.values(
        placedDevices.reduce<Record<string, { name: string; count: number; online: number }>>((acc, device) => {
          const key = device.room_name ?? 'Unplaced';
          const current = acc[key] ?? { name: key, count: 0, online: 0 };
          current.count += 1;
          if (device.status === 'online') {
            current.online += 1;
          }
          acc[key] = current;
          return acc;
        }, {}),
      ).sort((left, right) => left.name.localeCompare(right.name)),
    [placedDevices],
  );
  const recentStates = [...overview.states]
    .sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime())
    .slice(0, 4);

  if (!authenticated) {
    return (
      <SafeAreaView style={[styles.safeArea, { backgroundColor: palette.background }]}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.safeArea}>
          <ScrollView
            contentContainerStyle={styles.authScrollContent}
            keyboardShouldPersistTaps="handled">
            <View style={[styles.heroCard, { backgroundColor: palette.hero }]}>
              <Text style={[styles.eyebrow, { color: palette.eyebrow }]}>Alice</Text>
              <Text style={[styles.heroTitle, { color: palette.heroText }]}>
                Bring this home online.
              </Text>
              <Text style={[styles.heroBody, { color: palette.heroSubtle }]}>
                Set up the hub if it is brand new, then sign in to the same local Alice home that
                will own your rooms, devices, and assistant.
              </Text>
            </View>

            <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
              <Text style={[styles.panelTitle, { color: palette.text }]}>
                {setupStatus?.requires_onboarding ? 'Set up this home' : 'Sign in to your home'}
              </Text>
              <Text style={[styles.helperText, { color: palette.muted }]}>
                Use `alice.local` on a real hub or phone, `10.0.2.2` on Android emulator, and
                `127.0.0.1` on web or iOS simulator.
              </Text>

              <View style={styles.fieldGroup}>
                <Text style={[styles.fieldLabel, { color: palette.muted }]}>Hub API</Text>
                <TextInput
                  autoCapitalize="none"
                  autoCorrect={false}
                  onChangeText={setApiBaseUrlInput}
                  placeholder="http://alice.local:8000/api/v1"
                  placeholderTextColor={palette.placeholder}
                  style={[
                    styles.input,
                    { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
                  ]}
                  value={apiBaseUrlInput}
                />
              </View>

              {!authenticated && !setupLoading && setupStatus?.requires_onboarding ? (
                <>
                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: palette.muted }]}>Home name</Text>
                    <TextInput
                      onChangeText={setSetupSiteName}
                      placeholder="Alice Home"
                      placeholderTextColor={palette.placeholder}
                      style={[
                        styles.input,
                        { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
                      ]}
                      value={setupSiteName}
                    />
                  </View>

                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: palette.muted }]}>Timezone</Text>
                    <TextInput
                      autoCapitalize="none"
                      onChangeText={setSetupTimezone}
                      placeholder="Europe/London"
                      placeholderTextColor={palette.placeholder}
                      style={[
                        styles.input,
                        { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
                      ]}
                      value={setupTimezone}
                    />
                  </View>

                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: palette.muted }]}>Your name</Text>
                    <TextInput
                      onChangeText={setSetupOwnerName}
                      placeholder="Scott Jones"
                      placeholderTextColor={palette.placeholder}
                      style={[
                        styles.input,
                        { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
                      ]}
                      value={setupOwnerName}
                    />
                  </View>

                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: palette.muted }]}>Email</Text>
                    <TextInput
                      autoCapitalize="none"
                      autoCorrect={false}
                      keyboardType="email-address"
                      onChangeText={setSetupOwnerEmail}
                      placeholder="you@home.local"
                      placeholderTextColor={palette.placeholder}
                      style={[
                        styles.input,
                        { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
                      ]}
                      value={setupOwnerEmail}
                    />
                  </View>

                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: palette.muted }]}>Password</Text>
                    <TextInput
                      onChangeText={setSetupPassword}
                      placeholder="Choose a password"
                      placeholderTextColor={palette.placeholder}
                      secureTextEntry
                      style={[
                        styles.input,
                        { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
                      ]}
                      value={setupPassword}
                    />
                  </View>

                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: palette.muted }]}>Confirm password</Text>
                    <TextInput
                      onChangeText={setSetupPasswordConfirm}
                      placeholder="Repeat password"
                      placeholderTextColor={palette.placeholder}
                      secureTextEntry
                      style={[
                        styles.input,
                        { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
                      ]}
                      value={setupPasswordConfirm}
                    />
                  </View>

                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: palette.muted }]}>Rooms</Text>
                    <TextInput
                      multiline
                      onChangeText={setSetupRoomNames}
                      placeholder={DEFAULT_ROOM_NAMES}
                      placeholderTextColor={palette.placeholder}
                      style={[
                        styles.input,
                        styles.multilineInput,
                        { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
                      ]}
                      value={setupRoomNames}
                    />
                    <Text style={[styles.helperText, { color: palette.muted }]}>
                      Comma-separated. Start with the defaults and adjust them to match the house.
                    </Text>
                  </View>
                </>
              ) : (
                <>
                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: palette.muted }]}>Email</Text>
                    <TextInput
                      autoCapitalize="none"
                      autoCorrect={false}
                      keyboardType="email-address"
                      onChangeText={setEmail}
                      placeholder="you@home.local"
                      placeholderTextColor={palette.placeholder}
                      style={[
                        styles.input,
                        { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
                      ]}
                      value={email}
                    />
                  </View>

                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: palette.muted }]}>Password</Text>
                    <TextInput
                      onChangeText={setPassword}
                      placeholder="Your password"
                      placeholderTextColor={palette.placeholder}
                      secureTextEntry
                      style={[
                        styles.input,
                        { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
                      ]}
                      value={password}
                    />
                  </View>
                </>
              )}

              {setupLoading ? (
                <ActivityIndicator color={palette.primary} />
              ) : null}

              {setupStatus?.requires_onboarding ? setupError ? (
                <Text style={[styles.errorText, { color: palette.danger }]}>{setupError}</Text>
              ) : null : loginError ? (
                <Text style={[styles.errorText, { color: palette.danger }]}>{loginError}</Text>
              ) : null}

              <Pressable
                disabled={setupStatus?.requires_onboarding ? isSettingUp : isLoggingIn}
                onPress={setupStatus?.requires_onboarding ? handleSetup : handleLogin}
                style={[
                  styles.primaryButton,
                  { backgroundColor: palette.primary },
                  (setupStatus?.requires_onboarding ? isSettingUp : isLoggingIn) ? styles.disabledButton : null,
                ]}>
                {setupStatus?.requires_onboarding ? isSettingUp ? (
                  <ActivityIndicator color={palette.primaryText} />
                ) : (
                  <Text style={[styles.primaryButtonText, { color: palette.primaryText }]}>
                    Finish setup
                  </Text>
                ) : isLoggingIn ? (
                  <ActivityIndicator color={palette.primaryText} />
                ) : (
                  <Text style={[styles.primaryButtonText, { color: palette.primaryText }]}>
                    Sign in
                  </Text>
                )}
              </Pressable>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: palette.background }]}>
      <ScrollView
        contentContainerStyle={styles.screenContent}
        refreshControl={
          <RefreshControl
            onRefresh={() => void loadOverview(true)}
            refreshing={refreshing}
            tintColor={palette.primary}
          />
        }>
        <View style={[styles.heroCard, { backgroundColor: palette.hero }]}>
          <View style={styles.heroHeader}>
            <View style={styles.heroCopy}>
              <Text style={[styles.eyebrow, { color: palette.eyebrow }]}>Connected</Text>
              <Text style={[styles.heroTitle, { color: palette.heroText }]}>
                {overview.site?.site_name ?? 'Alice Home'}
              </Text>
              <Text style={[styles.heroBody, { color: palette.heroSubtle }]}>
                {user?.display_name} is connected to the local Alice hub.
              </Text>
            </View>
            <Pressable
              onPress={logout}
              style={[styles.secondaryButton, { borderColor: palette.heroBorder }]}>
              <Text style={[styles.secondaryButtonText, { color: palette.heroText }]}>Sign out</Text>
            </Pressable>
          </View>
        </View>

        <View style={styles.metricRow}>
          <MetricCard
            label="Devices"
            value={String(overview.devices.length)}
            accent={palette.metricA}
            palette={palette}
          />
          <MetricCard
            label="Online"
            value={String(onlineDevices)}
            accent={palette.metricB}
            palette={palette}
          />
          <MetricCard
            label="Entities"
            value={String(overview.entities.length)}
            accent={palette.metricC}
            palette={palette}
          />
        </View>

        {overview.devices.length > 0 ? (
          <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
            <Text style={[styles.panelTitle, { color: palette.text }]}>Rooms today</Text>
            <Text style={[styles.helperText, { color: palette.muted }]}>
              Alice organizes the home by room first, then by device inside each room.
            </Text>
            <View style={styles.roomSummaryRow}>
              <HealthPill
                label="Rooms"
                value={String(roomSummaries.length)}
                tone="neutral"
                palette={palette}
              />
              <HealthPill
                label="Placed"
                value={String(placedDevices.length)}
                tone="good"
                palette={palette}
              />
              <HealthPill
                label="Unplaced"
                value={String(unplacedDevices.length)}
                tone={unplacedDevices.length > 0 ? 'warning' : 'neutral'}
                palette={palette}
              />
            </View>

            {roomSummaries.length > 0 ? (
              roomSummaries.slice(0, 4).map((room) => (
                <View
                  key={room.name}
                  style={[styles.listCard, { backgroundColor: palette.subtlePanel, borderColor: palette.border }]}>
                  <Text style={[styles.listCardTitle, { color: palette.text }]}>{room.name}</Text>
                  <Text style={[styles.listCardBody, { color: palette.muted }]}>
                    {room.online} online of {room.count} device{room.count === 1 ? '' : 's'}
                  </Text>
                </View>
              ))
            ) : null}

            {unplacedDevices.length > 0 ? (
              <View
                style={[styles.listCard, { backgroundColor: palette.warnMuted, borderColor: palette.border }]}>
                <Text style={[styles.listCardTitle, { color: palette.warnText }]}>Needs placement</Text>
                <Text style={[styles.listCardBody, { color: palette.warnText }]}>
                  {unplacedDevices.map((device) => device.name).join(', ')}
                </Text>
              </View>
            ) : null}

            <View style={styles.actionRow}>
              <Pressable
                onPress={() => router.push('/(tabs)/devices')}
                style={[styles.primaryButton, styles.actionButton, { backgroundColor: palette.primary }]}>
                <Text style={[styles.primaryButtonText, { color: palette.primaryText }]}>
                  Open devices
                </Text>
              </Pressable>
              {unplacedDevices.length > 0 ? (
                <Pressable
                  onPress={() =>
                    router.push({
                      pathname: '/(tabs)/devices/[deviceId]',
                      params: { deviceId: unplacedDevices[0]?.id ?? '' },
                    })
                  }
                  style={[
                    styles.secondaryButton,
                    styles.actionButton,
                    { borderColor: palette.border, backgroundColor: palette.subtlePanel },
                  ]}>
                  <Text style={[styles.secondaryButtonText, { color: palette.text }]}>
                    Place next device
                  </Text>
                </Pressable>
              ) : null}
            </View>
          </View>
        ) : null}

        <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
          <Text style={[styles.panelTitle, { color: palette.text }]}>Stack health</Text>
          {loading && !overview.stackHealth ? (
            <ActivityIndicator color={palette.primary} style={styles.loader} />
          ) : overview.stackHealth ? (
            <View style={styles.stackGrid}>
              <HealthPill
                label="API"
                tone={overview.stackHealth.api_status === 'ok' ? 'good' : 'warning'}
                value={overview.stackHealth.api_status}
                palette={palette}
              />
              <HealthPill
                label="Broker"
                tone={overview.stackHealth.broker.connected ? 'good' : 'warning'}
                value={overview.stackHealth.broker.connected ? 'connected' : 'disconnected'}
                palette={palette}
              />
              <HealthPill
                label="Timeout"
                tone="neutral"
                value={`${overview.stackHealth.devices.timeout_seconds}s`}
                palette={palette}
              />
            </View>
          ) : null}

          {overview.stackHealth ? (
            <View style={styles.detailList}>
              <Text style={[styles.detailLine, { color: palette.muted }]}>
                Broker target: {overview.stackHealth.broker.host}:{overview.stackHealth.broker.port}
              </Text>
              <Text style={[styles.detailLine, { color: palette.muted }]}>
                Latest ack: {formatCommandEvent(overview.stackHealth.latest_command_ack)}
              </Text>
            </View>
          ) : null}
        </View>

        <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
          <Text style={[styles.panelTitle, { color: palette.text }]}>Recent state changes</Text>
          {recentStates.length === 0 ? (
            <Text style={[styles.helperText, { color: palette.muted }]}>No state has been projected yet.</Text>
          ) : (
            recentStates.map((entry) => (
              <View
                key={entry.entity_id}
                style={[styles.listCard, { backgroundColor: palette.subtlePanel, borderColor: palette.border }]}>
                <Text style={[styles.listCardTitle, { color: palette.text }]}>{entry.entity_id}</Text>
                <Text style={[styles.listCardBody, { color: palette.muted }]}>
                  {formatStateValue(entry.value)}
                </Text>
                <Text style={[styles.listCardMeta, { color: palette.placeholder }]}>
                  {formatTimestamp(entry.updated_at)}
                </Text>
              </View>
            ))
          )}
        </View>

        {overview.devices.length === 0 ? (
          <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
            <Text style={[styles.panelTitle, { color: palette.text }]}>Next step</Text>
            <Text style={[styles.helperText, { color: palette.muted }]}>
              Add your first device from the Add tab. Alice will bring it onto the home network,
              attach it to a room, and make it available for control right away.
            </Text>
            <Pressable
              onPress={() => router.push('/(tabs)/onboarding')}
              style={[styles.primaryButton, { backgroundColor: palette.primary }]}>
              <Text style={[styles.primaryButtonText, { color: palette.primaryText }]}>
                Add your first device
              </Text>
            </Pressable>
          </View>
        ) : null}

        {loadError ? (
          <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
            <Text style={[styles.errorText, { color: palette.danger }]}>{loadError}</Text>
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function MetricCard({
  label,
  value,
  accent,
  palette,
}: {
  label: string;
  value: string;
  accent: string;
  palette: ReturnType<typeof getMobilePalette>;
}) {
  return (
    <View style={[styles.metricCard, { backgroundColor: palette.panel, borderColor: palette.border }]}>
      <View style={[styles.metricAccent, { backgroundColor: accent }]} />
      <Text style={[styles.metricLabel, { color: palette.muted }]}>{label}</Text>
      <Text style={[styles.metricValue, { color: palette.text }]}>{value}</Text>
    </View>
  );
}

function HealthPill({
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
    <View style={[styles.healthPill, { backgroundColor }]}>
      <Text style={[styles.healthPillLabel, { color: palette.muted }]}>{label}</Text>
      <Text style={[styles.healthPillValue, { color: textColor }]}>{value}</Text>
    </View>
  );
}

function formatCommandEvent(event: StackHealth['latest_command_ack']): string {
  if (!event) {
    return 'No recent acknowledgement';
  }

  const command = String(event.metadata.command ?? event.action);
  const status = event.metadata.status ? ` | ${String(event.metadata.status)}` : '';
  return `${command}${status} | ${formatTimestamp(event.created_at)}`;
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
  authScrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 20,
    gap: 18,
  },
  screenContent: {
    padding: 20,
    gap: 16,
  },
  heroCard: {
    borderRadius: 28,
    padding: 22,
  },
  heroHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 16,
  },
  heroCopy: {
    flex: 1,
    gap: 8,
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
  panel: {
    borderRadius: 24,
    borderWidth: 1,
    padding: 18,
    gap: 14,
  },
  panelTitle: {
    fontSize: 20,
    fontWeight: '700',
  },
  helperText: {
    fontSize: 14,
    lineHeight: 20,
  },
  fieldGroup: {
    gap: 8,
  },
  fieldLabel: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  input: {
    borderRadius: 16,
    borderWidth: 1,
    fontSize: 16,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  multilineInput: {
    minHeight: 96,
    textAlignVertical: 'top',
  },
  primaryButton: {
    alignItems: 'center',
    borderRadius: 16,
    justifyContent: 'center',
    minHeight: 54,
    paddingHorizontal: 18,
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: '700',
  },
  secondaryButton: {
    borderRadius: 14,
    borderWidth: 1,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  secondaryButtonText: {
    fontSize: 14,
    fontWeight: '700',
  },
  disabledButton: {
    opacity: 0.7,
  },
  errorText: {
    fontSize: 14,
    lineHeight: 20,
  },
  metricRow: {
    flexDirection: 'row',
    gap: 12,
  },
  metricCard: {
    flex: 1,
    borderRadius: 20,
    borderWidth: 1,
    minHeight: 120,
    overflow: 'hidden',
    padding: 16,
  },
  metricAccent: {
    borderRadius: 999,
    height: 8,
    marginBottom: 14,
    width: 44,
  },
  metricLabel: {
    fontSize: 13,
    marginBottom: 6,
  },
  metricValue: {
    fontSize: 30,
    fontWeight: '700',
  },
  loader: {
    paddingVertical: 16,
  },
  stackGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  roomSummaryRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  healthPill: {
    borderRadius: 18,
    minWidth: '31%',
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  healthPillLabel: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.7,
    marginBottom: 4,
    textTransform: 'uppercase',
  },
  healthPillValue: {
    fontSize: 16,
    fontWeight: '700',
  },
  detailList: {
    gap: 6,
  },
  detailLine: {
    fontSize: 14,
    lineHeight: 20,
  },
  listCard: {
    borderRadius: 18,
    borderWidth: 1,
    padding: 14,
    gap: 6,
  },
  listCardTitle: {
    fontSize: 15,
    fontWeight: '700',
  },
  listCardBody: {
    fontSize: 14,
    lineHeight: 20,
  },
  listCardMeta: {
    fontSize: 12,
  },
  actionRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  actionButton: {
    flex: 1,
  },
});
