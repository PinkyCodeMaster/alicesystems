import { router } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { CameraView, type BarcodeScanningResult, useCameraPermissions } from 'expo-camera';
import { SafeAreaView } from 'react-native-safe-area-context';

import {
  apiRequest,
  createBootstrapRecord,
  createProvisioningSession,
  createRoomRequest,
  formatTimestamp,
  getProvisioningSessionStatus,
  isUnauthorizedError,
  normalizeDeviceSetupBaseUrl,
  sendLocalDeviceProvisioning,
  sendSwitchCommand,
  updateDeviceRequest,
  type DeviceDetail,
  type LocalDeviceProvisioningResponse,
  type ProvisioningSessionResponse,
  type ProvisioningSessionStatusResponse,
  type Room,
} from '@/lib/alice-api';
import { parseAliceDeviceQrPayload, type AliceDeviceQrPayload } from '@/lib/alice-device-qr';
import {
  connectToSetupAccessPoint,
  ensureWifiProvisioningPermissions,
  isNativeWifiProvisioningAvailable,
  releaseSetupAccessPointBinding,
} from '@/lib/alice-wifi-provisioning';
import { getMobilePalette } from '@/lib/mobile-theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { useAliceSession } from '@/providers/alice-session';

const SESSION_POLL_INTERVAL_MS = 3000;

export default function OnboardingScreen() {
  const { apiBaseUrl, authenticated, logout, token } = useAliceSession();
  const colorScheme = useColorScheme();
  const palette = getMobilePalette(colorScheme);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();

  const [bootstrapId, setBootstrapId] = useState('');
  const [setupCode, setSetupCode] = useState('');
  const [qrPayloadInput, setQrPayloadInput] = useState('');
  const [requestedDeviceName, setRequestedDeviceName] = useState('');
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [scannedPayload, setScannedPayload] = useState<AliceDeviceQrPayload | null>(null);
  const [scannerActive, setScannerActive] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<string | null>(null);
  const [showAdvancedClaim, setShowAdvancedClaim] = useState(false);
  const [showAdvancedTransport, setShowAdvancedTransport] = useState(false);

  const [rooms, setRooms] = useState<Room[]>([]);
  const [roomsLoading, setRoomsLoading] = useState(false);
  const [roomsRefreshing, setRoomsRefreshing] = useState(false);
  const [roomsError, setRoomsError] = useState<string | null>(null);
  const [newRoomName, setNewRoomName] = useState('');
  const [creatingRoom, setCreatingRoom] = useState(false);
  const [createRoomError, setCreateRoomError] = useState<string | null>(null);
  const [createRoomSuccess, setCreateRoomSuccess] = useState<string | null>(null);

  const [activeSession, setActiveSession] = useState<ProvisioningSessionResponse | null>(null);
  const [sessionStatus, setSessionStatus] = useState<ProvisioningSessionStatusResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);

  const [deviceSetupSsid, setDeviceSetupSsid] = useState('');
  const [deviceSetupPassword, setDeviceSetupPassword] = useState('alice-setup');
  const [deviceSetupBaseUrl, setDeviceSetupBaseUrl] = useState('http://192.168.4.1');
  const [wifiSsid, setWifiSsid] = useState('');
  const [wifiPassword, setWifiPassword] = useState('');
  const [nativeWifiAvailable, setNativeWifiAvailable] = useState(false);
  const [nativeWifiReady, setNativeWifiReady] = useState(false);
  const [deviceApStatus, setDeviceApStatus] = useState<string | null>(null);
  const [deviceApJoining, setDeviceApJoining] = useState(false);
  const [localProvisioning, setLocalProvisioning] = useState(false);
  const [localProvisioningError, setLocalProvisioningError] = useState<string | null>(null);
  const [localProvisioningResult, setLocalProvisioningResult] = useState<LocalDeviceProvisioningResponse | null>(null);
  const [finalizingClaim, setFinalizingClaim] = useState(false);
  const [finalizeError, setFinalizeError] = useState<string | null>(null);
  const [finalizeSuccess, setFinalizeSuccess] = useState<string | null>(null);
  const [claimedDeviceDetail, setClaimedDeviceDetail] = useState<DeviceDetail | null>(null);
  const [claimedDeviceLoading, setClaimedDeviceLoading] = useState(false);
  const [claimedDeviceError, setClaimedDeviceError] = useState<string | null>(null);
  const [claimedActionBusy, setClaimedActionBusy] = useState(false);

  const selectedRoomName = useMemo(
    () => rooms.find((room) => room.id === selectedRoomId)?.name ?? 'No room yet',
    [rooms, selectedRoomId],
  );
  const claimReady = Boolean(bootstrapId.trim() && setupCode.trim());
  const claimedDeviceId = sessionStatus?.claimed_device_id ?? null;
  const sessionClaimed = sessionStatus?.status === 'claimed' && Boolean(claimedDeviceId);
  const relayEntity = useMemo(
    () =>
      claimedDeviceDetail?.entities.find(
        (entity) => entity.writable === 1 && entity.kind === 'switch.relay',
      ) ?? null,
    [claimedDeviceDetail],
  );
  const sensorEntityLabels = useMemo(() => {
    if (!claimedDeviceDetail) {
      return [];
    }

    const labels = new Set<string>();
    for (const entity of claimedDeviceDetail.entities) {
      if (entity.kind === 'sensor.motion') {
        labels.add('motion');
      } else if (entity.kind === 'sensor.temperature') {
        labels.add('temperature');
      } else if (entity.kind === 'sensor.illuminance') {
        labels.add('light');
      }
    }
    return Array.from(labels);
  }, [claimedDeviceDetail]);
  const relayStateOn =
    relayEntity && typeof relayEntity.state?.on === 'boolean' ? Boolean(relayEntity.state.on) : null;
  const primaryOpenActionLabel = relayEntity
    ? 'Open light controls'
    : sensorEntityLabels.length > 0
      ? 'Watch live readings'
      : 'Open device';

  useEffect(() => {
    let active = true;

    async function loadNativeWifiAvailability() {
      if (Platform.OS !== 'android') {
        if (active) {
          setNativeWifiAvailable(false);
          setNativeWifiReady(true);
        }
        return;
      }

      try {
        const available = await isNativeWifiProvisioningAvailable();
        if (active) {
          setNativeWifiAvailable(available);
        }
      } catch {
        if (active) {
          setNativeWifiAvailable(false);
        }
      } finally {
        if (active) {
          setNativeWifiReady(true);
        }
      }
    }

    void loadNativeWifiAvailability();

    return () => {
      active = false;
      void releaseSetupAccessPointBinding();
    };
  }, []);

  const loadRooms = useCallback(
    async (isPullToRefresh: boolean) => {
      if (!token) {
        return;
      }

      if (isPullToRefresh) {
        setRoomsRefreshing(true);
      } else {
        setRoomsLoading(true);
      }

      try {
        const response = await apiRequest<{ items: Room[] }>(apiBaseUrl, '/rooms', undefined, token);
        setRooms(response.items);
        setRoomsError(null);
      } catch (error) {
        if (isUnauthorizedError(error)) {
          logout();
        }
        setRoomsError(error instanceof Error ? error.message : 'Unable to load rooms.');
      } finally {
        setRoomsLoading(false);
        setRoomsRefreshing(false);
      }
    },
    [apiBaseUrl, logout, token],
  );

  const refreshSessionStatus = useCallback(async () => {
    if (!token || !activeSession) {
      return;
    }

    setPolling(true);
    try {
      const status = await getProvisioningSessionStatus(apiBaseUrl, token, activeSession.session_id);
      setSessionStatus(status);
      setSessionError(null);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        logout();
      }
      setSessionError(error instanceof Error ? error.message : 'Unable to refresh claim status.');
    } finally {
      setPolling(false);
    }
  }, [activeSession, apiBaseUrl, logout, token]);

  useEffect(() => {
    if (!authenticated || !token) {
      setRooms([]);
      setActiveSession(null);
      setSessionStatus(null);
      return;
    }

    void loadRooms(false);
  }, [authenticated, loadRooms, token]);

  useEffect(() => {
    if (!activeSession || !token) {
      return;
    }

    void refreshSessionStatus();
    if (sessionStatus?.status && sessionStatus.status !== 'pending') {
      return;
    }
    const interval = setInterval(() => {
      void refreshSessionStatus();
    }, SESSION_POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [activeSession, refreshSessionStatus, sessionStatus?.status, token]);

  const loadClaimedDeviceDetail = useCallback(async () => {
    if (!token || !claimedDeviceId) {
      setClaimedDeviceDetail(null);
      setClaimedDeviceError(null);
      return;
    }

    setClaimedDeviceLoading(true);
    try {
      const detail = await apiRequest<DeviceDetail>(
        apiBaseUrl,
        `/devices/${claimedDeviceId}`,
        undefined,
        token,
      );
      setClaimedDeviceDetail(detail);
      setClaimedDeviceError(null);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        logout();
      }
      setClaimedDeviceError(
        error instanceof Error ? error.message : 'Unable to load the claimed device details.',
      );
    } finally {
      setClaimedDeviceLoading(false);
    }
  }, [apiBaseUrl, claimedDeviceId, logout, token]);

  useEffect(() => {
    if (!sessionClaimed) {
      setClaimedDeviceDetail(null);
      setClaimedDeviceError(null);
      return;
    }

    void loadClaimedDeviceDetail();
  }, [loadClaimedDeviceDetail, sessionClaimed]);

  async function handleStartSession() {
    if (!token) {
      return;
    }

    setSubmitting(true);
    setSessionError(null);

    try {
      if (
        scannedPayload &&
        scannedPayload.bootstrapId === bootstrapId.trim() &&
        scannedPayload.setupCode === setupCode.trim()
      ) {
        await ensureBootstrapRecordFromQr(scannedPayload, token);
      }

      const session = await createProvisioningSession(apiBaseUrl, token, {
        bootstrapId,
        setupCode,
        requestedDeviceName,
        roomId: selectedRoomId,
      });
      setActiveSession(session);
      setSessionStatus(null);
      setLocalProvisioningError(null);
      setLocalProvisioningResult(null);
      setFinalizeError(null);
      setFinalizeSuccess(null);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        logout();
      }
      setSessionError(error instanceof Error ? error.message : 'Unable to start claim session.');
    } finally {
      setSubmitting(false);
    }
  }

  async function ensureBootstrapRecordFromQr(payload: AliceDeviceQrPayload, currentToken: string) {
    if (!payload.model || !payload.deviceType) {
      return;
    }

    try {
      await createBootstrapRecord(apiBaseUrl, currentToken, {
        bootstrapId: payload.bootstrapId,
        setupCode: payload.setupCode,
        model: payload.model,
        deviceType: payload.deviceType,
        metadata: {
          source: 'mobile_qr_scan',
        },
      });
      setScanStatus(`Registered ${payload.bootstrapId} on this hub`);
    } catch (error) {
      if (!(error instanceof Error)) {
        throw error;
      }
      if (!error.message.includes('already exists')) {
        throw error;
      }
    }
  }

  function applyQrPayload(rawPayload: string) {
    const payload = parseAliceDeviceQrPayload(rawPayload);
    setScannedPayload(payload);
    setBootstrapId(payload.bootstrapId);
    setSetupCode(payload.setupCode);
    setQrPayloadInput(rawPayload.trim());
    if (payload.setupApSsid) {
      setDeviceSetupSsid(payload.setupApSsid);
    }
    setScanError(null);
    setScanStatus(
      `Loaded ${payload.bootstrapId}${payload.model ? ` (${payload.model})` : ''}${
        payload.deviceType ? ` / ${payload.deviceType}` : ''
      }`,
    );
  }

  async function handleOpenScanner() {
    setScanError(null);
    const permission = cameraPermission?.granted ? cameraPermission : await requestCameraPermission();
    if (!permission?.granted) {
      setScanError('Camera permission is required to scan device QR codes.');
      return;
    }
    setScannerActive(true);
  }

  function handleBarcodeScanned(result: BarcodeScanningResult) {
    try {
      applyQrPayload(result.data);
      setScannerActive(false);
    } catch (error) {
      setScanError(error instanceof Error ? error.message : 'Unable to read the scanned QR payload.');
    }
  }

  function handleApplyQrPayloadInput() {
    try {
      applyQrPayload(qrPayloadInput);
    } catch (error) {
      setScanError(error instanceof Error ? error.message : 'Unable to use the QR payload.');
    }
  }

  async function handleSendToDevice() {
    if (!activeSession) {
      return;
    }

    setLocalProvisioning(true);
    setLocalProvisioningError(null);

    try {
      const result = await sendLocalDeviceProvisioning(deviceSetupBaseUrl, {
        bootstrapId: activeSession.bootstrap_id,
        claimToken: activeSession.claim_token,
        wifiSsid,
        wifiPassword,
        hubApiBaseUrl: apiBaseUrl,
      });
      setLocalProvisioningResult(result);
    } catch (error) {
      setLocalProvisioningError(error instanceof Error ? error.message : 'Unable to send setup to the device.');
    } finally {
      setLocalProvisioning(false);
    }
  }

  async function handleAutoJoinAndSendToDevice() {
    if (!activeSession) {
      return;
    }

    setDeviceApJoining(true);
    setLocalProvisioning(true);
    setLocalProvisioningError(null);
    setLocalProvisioningResult(null);
    setDeviceApStatus(null);

    try {
      const targetSsid = deviceSetupSsid.trim();
      if (!targetSsid) {
        throw new Error('Device setup Wi-Fi name is required.');
      }

      await ensureWifiProvisioningPermissions();
      setDeviceApStatus(`Joining ${targetSsid}...`);
      await connectToSetupAccessPoint(targetSsid, deviceSetupPassword);

      setDeviceApStatus(`Connected to ${targetSsid}. Sending setup payload...`);
      const result = await sendLocalDeviceProvisioning(deviceSetupBaseUrl, {
        bootstrapId: activeSession.bootstrap_id,
        claimToken: activeSession.claim_token,
        wifiSsid,
        wifiPassword,
        hubApiBaseUrl: apiBaseUrl,
      });
      setLocalProvisioningResult(result);

      setDeviceApStatus('Setup accepted. Releasing the device network and returning to your normal connection...');
      await releaseSetupAccessPointBinding();
      setDeviceApStatus('Returned from the device network. Waiting for the device to join your home Wi-Fi and finish the claim.');
    } catch (error) {
      await releaseSetupAccessPointBinding();
      setDeviceApStatus(null);
      setLocalProvisioningError(error instanceof Error ? error.message : 'Unable to hand setup to the device over Wi-Fi.');
    } finally {
      setDeviceApJoining(false);
      setLocalProvisioning(false);
    }
  }

  async function handleFinalizeClaim() {
    if (!token || !sessionStatus?.claimed_device_id) {
      return;
    }

    const resolvedName =
      requestedDeviceName.trim() ||
      scannedPayload?.model ||
      'Alice device';

    setFinalizingClaim(true);
    setFinalizeError(null);
    setFinalizeSuccess(null);

    try {
      await updateDeviceRequest(apiBaseUrl, token, sessionStatus.claimed_device_id, {
        name: resolvedName,
        room_id: selectedRoomId,
      });
      if (!requestedDeviceName.trim()) {
        setRequestedDeviceName(resolvedName);
      }
      setFinalizeSuccess(`Saved as ${resolvedName} in ${selectedRoomName}.`);
      await loadClaimedDeviceDetail();
    } catch (error) {
      if (isUnauthorizedError(error)) {
        logout();
      }
      setFinalizeError(error instanceof Error ? error.message : 'Unable to save device details.');
    } finally {
      setFinalizingClaim(false);
    }
  }

  async function handleToggleClaimedRelay() {
    if (!token || !relayEntity || relayStateOn === null || claimedActionBusy) {
      return;
    }

    setClaimedActionBusy(true);
    setClaimedDeviceError(null);
    try {
      await sendSwitchCommand(apiBaseUrl, token, relayEntity.id, !relayStateOn);
      await loadClaimedDeviceDetail();
    } catch (error) {
      if (isUnauthorizedError(error)) {
        logout();
      }
      setClaimedDeviceError(
        error instanceof Error ? error.message : 'Unable to test this device right now.',
      );
    } finally {
      setClaimedActionBusy(false);
    }
  }

  function handleReset() {
    setBootstrapId('');
    setSetupCode('');
    setQrPayloadInput('');
    setRequestedDeviceName('');
    setSelectedRoomId(null);
    setScannedPayload(null);
    setActiveSession(null);
    setSessionStatus(null);
    setSessionError(null);
    setScannerActive(false);
    setScanError(null);
    setScanStatus(null);
    setDeviceApStatus(null);
    setLocalProvisioningError(null);
    setLocalProvisioningResult(null);
    setFinalizeError(null);
    setFinalizeSuccess(null);
    setClaimedDeviceDetail(null);
    setClaimedDeviceLoading(false);
    setClaimedDeviceError(null);
    setClaimedActionBusy(false);
  }

  if (!authenticated) {
    return (
      <SafeAreaView style={[styles.safeArea, { backgroundColor: palette.background }]}>
        <View style={styles.emptyState}>
          <Text style={[styles.emptyTitle, { color: palette.text }]}>Sign in on Home</Text>
          <Text style={[styles.emptyBody, { color: palette.muted }]}>
            Device claim belongs to the owner flow, so onboarding unlocks only after Home OS login.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  const canAutoJoinDeviceAp = Platform.OS === 'android' && nativeWifiAvailable;
  const handleRequestedDeviceNameChange = (value: string) => {
    setRequestedDeviceName(value);
    setFinalizeError(null);
    setFinalizeSuccess(null);
  };

  const handleRoomSelection = (roomId: string | null) => {
    setSelectedRoomId(roomId);
    setFinalizeError(null);
    setFinalizeSuccess(null);
  };

  async function handleCreateRoom() {
    if (!token || !newRoomName.trim()) {
      return;
    }

    setCreatingRoom(true);
    setCreateRoomError(null);
    setCreateRoomSuccess(null);

    try {
      const room = await createRoomRequest(apiBaseUrl, token, newRoomName);
      setRooms((current) => {
        const next = current.some((item) => item.id === room.id)
          ? current.map((item) => (item.id === room.id ? room : item))
          : [...current, room];
        return [...next].sort((left, right) => left.name.localeCompare(right.name));
      });
      handleRoomSelection(room.id);
      setNewRoomName('');
      setCreateRoomSuccess(`Added ${room.name}.`);
      setRoomsError(null);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        logout();
      }
      setCreateRoomError(error instanceof Error ? error.message : 'Unable to create room.');
    } finally {
      setCreatingRoom(false);
    }
  }

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: palette.background }]}>
      <ScrollView
        contentContainerStyle={styles.screenContent}
        refreshControl={
          <RefreshControl
            onRefresh={() => void loadRooms(true)}
            refreshing={roomsRefreshing}
            tintColor={palette.primary}
          />
        }>
        <View style={[styles.headerCard, { backgroundColor: palette.hero }]}>
          <Text style={[styles.eyebrow, { color: palette.eyebrow }]}>Add Device</Text>
          <Text style={[styles.headerTitle, { color: palette.heroText }]}>Scan and add</Text>
          <Text style={[styles.headerBody, { color: palette.heroSubtle }]}>
            Scan the Alice QR code, choose a name and room, then hand the device onto your home
            Wi-Fi so it can finish joining this household.
          </Text>
        </View>

        <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
          <Text style={[styles.panelTitle, { color: palette.text }]}>1. Identify this device</Text>

          <View style={[styles.infoCard, { backgroundColor: palette.subtlePanel, borderColor: palette.border }]}>
            <Text style={[styles.infoLabel, { color: palette.muted }]}>Scan the device QR</Text>
            <Text style={[styles.helperText, { color: palette.muted }]}>
              The normal path is to scan the printed Alice QR code on the device or its box.
            </Text>

            <View style={styles.qrActionRow}>
              <Pressable
                onPress={() => void handleOpenScanner()}
                style={[
                  styles.secondaryActionButton,
                  styles.qrActionButton,
                  { borderColor: palette.border, backgroundColor: palette.subtlePanel },
                ]}>
                <Text style={[styles.secondaryActionButtonText, { color: palette.text }]}>
                  {scannerActive ? 'Scanner active' : 'Scan QR'}
                </Text>
              </Pressable>

              {scannerActive ? (
                <Pressable
                  onPress={() => setScannerActive(false)}
                  style={[
                    styles.secondaryActionButton,
                    styles.qrActionButton,
                    { borderColor: palette.border, backgroundColor: palette.subtlePanel },
                  ]}>
                  <Text style={[styles.secondaryActionButtonText, { color: palette.text }]}>Stop scan</Text>
                </Pressable>
              ) : null}
            </View>

            {scannerActive ? (
              <View style={[styles.cameraShell, { borderColor: palette.border, backgroundColor: palette.input }]}>
                <CameraView
                  barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
                  onBarcodeScanned={scannerActive ? handleBarcodeScanned : undefined}
                  style={styles.cameraView}
                />
              </View>
            ) : null}

            {scanStatus ? (
              <Text style={[styles.successText, { color: palette.goodText }]}>{scanStatus}</Text>
            ) : null}

            {scanError ? (
              <Text style={[styles.errorText, { color: palette.danger }]}>{scanError}</Text>
            ) : null}

            <Pressable
              onPress={() => setShowAdvancedClaim((current) => !current)}
              style={[
                styles.secondaryActionButton,
                { borderColor: palette.border, backgroundColor: palette.subtlePanel },
              ]}>
              <Text style={[styles.secondaryActionButtonText, { color: palette.text }]}>
                {showAdvancedClaim ? 'Hide advanced setup details' : 'Use advanced setup details'}
              </Text>
            </Pressable>

            {showAdvancedClaim ? (
              <View style={styles.fieldGroup}>
                <Text style={[styles.helperText, { color: palette.muted }]}>
                  Use this only for recovery or pre-release devices when the printed QR path is not
                  available.
                </Text>
                <Field
                  label="QR payload"
                  palette={palette}
                  placeholder='{"v":1,"bootstrap_id":"boot_sensor_hall_01","setup_code":"482913"}'
                  value={qrPayloadInput}
                  onChangeText={setQrPayloadInput}
                  autoCapitalize="none"
                />
                <Pressable
                  disabled={!qrPayloadInput.trim()}
                  onPress={handleApplyQrPayloadInput}
                  style={[
                    styles.secondaryActionButton,
                    { borderColor: palette.border, backgroundColor: palette.subtlePanel },
                    !qrPayloadInput.trim() ? styles.disabledButton : null,
                  ]}>
                  <Text style={[styles.secondaryActionButtonText, { color: palette.text }]}>
                    Use pasted QR payload
                  </Text>
                </Pressable>

                <Field
                  label="Bootstrap ID"
                  palette={palette}
                  placeholder="boot_sensor_hall_01"
                  value={bootstrapId}
                  onChangeText={setBootstrapId}
                  autoCapitalize="none"
                />

                <Field
                  label="Setup code"
                  palette={palette}
                  placeholder="482913"
                  value={setupCode}
                  onChangeText={setSetupCode}
                  autoCapitalize="none"
                />
              </View>
            ) : null}
          </View>

          {claimReady && !showAdvancedClaim ? (
            <View style={[styles.infoCard, { backgroundColor: palette.subtlePanel, borderColor: palette.border }]}>
              <Text style={[styles.infoLabel, { color: palette.muted }]}>Ready to add</Text>
              <Text style={[styles.infoValue, { color: palette.text }]}>
                {scannedPayload?.model ?? 'Alice device'}
              </Text>
              <Text style={[styles.helperText, { color: palette.muted }]}>
                Alice has the claim details it needs. Choose how this device should appear in your
                home.
              </Text>
            </View>
          ) : null}

          <Field
            label="Name"
            palette={palette}
            placeholder="Hall Sensor"
            value={requestedDeviceName}
            onChangeText={handleRequestedDeviceNameChange}
          />

          <View style={styles.fieldGroup}>
            <Text style={[styles.fieldLabel, { color: palette.muted }]}>Room</Text>
            {roomsLoading && rooms.length === 0 ? (
              <ActivityIndicator color={palette.primary} style={styles.inlineLoader} />
            ) : (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.roomRow}>
                <RoomChip
                  active={selectedRoomId === null}
                  label="No room yet"
                  onPress={() => handleRoomSelection(null)}
                  palette={palette}
                />
                {rooms.map((room) => (
                  <RoomChip
                    key={room.id}
                    active={selectedRoomId === room.id}
                    label={room.name}
                    onPress={() => handleRoomSelection(room.id)}
                    palette={palette}
                  />
                ))}
              </ScrollView>
            )}
            {roomsError ? (
              <Text style={[styles.errorText, { color: palette.danger }]}>{roomsError}</Text>
            ) : null}
            <View style={[styles.infoCard, { backgroundColor: palette.subtlePanel, borderColor: palette.border }]}>
              <Text style={[styles.infoLabel, { color: palette.muted }]}>Need a new room?</Text>
              <Text style={[styles.helperText, { color: palette.muted }]}>
                Add the room here so this device lands in the right place immediately.
              </Text>
              <Field
                label="New room"
                palette={palette}
                placeholder="Utility Room"
                value={newRoomName}
                onChangeText={(value) => {
                  setNewRoomName(value);
                  setCreateRoomError(null);
                  setCreateRoomSuccess(null);
                }}
              />
              {createRoomError ? (
                <Text style={[styles.errorText, { color: palette.danger }]}>{createRoomError}</Text>
              ) : null}
              {createRoomSuccess ? (
                <Text style={[styles.successText, { color: palette.goodText }]}>{createRoomSuccess}</Text>
              ) : null}
              <Pressable
                disabled={creatingRoom || !newRoomName.trim()}
                onPress={() => void handleCreateRoom()}
                style={[
                  styles.secondaryActionButton,
                  { borderColor: palette.border, backgroundColor: palette.subtlePanel },
                  (creatingRoom || !newRoomName.trim()) ? styles.disabledButton : null,
                ]}>
                {creatingRoom ? (
                  <ActivityIndicator color={palette.text} />
                ) : (
                  <Text style={[styles.secondaryActionButtonText, { color: palette.text }]}>
                    Add room
                  </Text>
                )}
              </Pressable>
            </View>
          </View>

          {sessionError ? (
            <Text style={[styles.errorText, { color: palette.danger }]}>{sessionError}</Text>
          ) : null}

          <Pressable
            disabled={submitting || !claimReady}
            onPress={handleStartSession}
            style={[
              styles.primaryButton,
              { backgroundColor: palette.primary },
              (submitting || !claimReady) ? styles.disabledButton : null,
            ]}>
            {submitting ? (
              <ActivityIndicator color={palette.primaryText} />
            ) : (
              <Text style={[styles.primaryButtonText, { color: palette.primaryText }]}>
                Continue
              </Text>
            )}
          </Pressable>
        </View>

        {activeSession ? (
          <View style={[styles.panel, { backgroundColor: palette.panel, borderColor: palette.border }]}>
            <View style={styles.sessionHeader}>
              <View style={styles.sessionHeaderCopy}>
                <Text style={[styles.panelTitle, { color: palette.text }]}>2. Join your home Wi-Fi</Text>
                <Text style={[styles.helperText, { color: palette.muted }]}>
                  {requestedDeviceName.trim() || scannedPayload?.model || 'This device'} will appear in{' '}
                  {selectedRoomName}. Session expires {formatTimestamp(activeSession.expires_at)}.
                </Text>
              </View>
              <Pressable onPress={handleReset} style={[styles.secondaryButton, { borderColor: palette.border }]}>
                <Text style={[styles.secondaryButtonText, { color: palette.text }]}>Start over</Text>
              </Pressable>
            </View>

            <View style={[styles.infoCard, { backgroundColor: palette.subtlePanel, borderColor: palette.border }]}>
              <Text style={[styles.infoLabel, { color: palette.muted }]}>Device handoff</Text>
              <Text style={[styles.helperText, { color: palette.muted }]}>
                Alice will hand the device your home Wi-Fi details, then wait for it to complete
                the claim with the hub.
              </Text>

              <Field
                label="Home Wi-Fi name"
                palette={palette}
                placeholder="MyHomeWiFi"
                value={wifiSsid}
                onChangeText={setWifiSsid}
                autoCapitalize="none"
              />

              <Field
                label="Home Wi-Fi password"
                palette={palette}
                placeholder="Enter your Wi-Fi password"
                value={wifiPassword}
                onChangeText={setWifiPassword}
                secureTextEntry
              />

              {Platform.OS === 'android' && !nativeWifiReady ? (
                <ActivityIndicator color={palette.primary} style={styles.inlineLoader} />
              ) : null}

              {Platform.OS === 'android' && nativeWifiReady && !nativeWifiAvailable ? (
                <Text style={[styles.helperText, { color: palette.warnText }]}>
                  Automatic Wi-Fi handoff needs an Android development build with the Alice native
                  Wi-Fi module. Otherwise, use the advanced handoff option below.
                </Text>
              ) : null}

              {deviceApStatus ? (
                <Text style={[styles.helperText, { color: palette.goodText }]}>{deviceApStatus}</Text>
              ) : null}

              {localProvisioningError ? (
                <Text style={[styles.errorText, { color: palette.danger }]}>{localProvisioningError}</Text>
              ) : null}

              {localProvisioningResult?.accepted ? (
                <Text style={[styles.successText, { color: palette.goodText }]}>
                  Setup accepted. The device should restart, join your Wi-Fi, and finish claiming
                  itself into Alice.
                </Text>
              ) : null}

              {canAutoJoinDeviceAp ? (
                <Pressable
                  disabled={localProvisioning || deviceApJoining || !activeSession.claim_token || !deviceSetupSsid.trim()}
                  onPress={handleAutoJoinAndSendToDevice}
                  style={[
                    styles.primaryButton,
                    { backgroundColor: palette.primary },
                    (localProvisioning || deviceApJoining || !activeSession.claim_token || !deviceSetupSsid.trim())
                      ? styles.disabledButton
                      : null,
                  ]}>
                  {localProvisioning || deviceApJoining ? (
                    <ActivityIndicator color={palette.primaryText} />
                  ) : (
                    <Text style={[styles.primaryButtonText, { color: palette.primaryText }]}>
                      Connect and finish setup
                    </Text>
                  )}
                </Pressable>
              ) : null}

              <Pressable
                onPress={() => setShowAdvancedTransport((current) => !current)}
                style={[
                  styles.secondaryActionButton,
                  { borderColor: palette.border, backgroundColor: palette.subtlePanel },
                ]}>
                <Text style={[styles.secondaryActionButtonText, { color: palette.text }]}>
                  {showAdvancedTransport ? 'Hide advanced handoff' : 'Use advanced handoff'}
                </Text>
              </Pressable>

              {showAdvancedTransport ? (
                <View style={styles.fieldGroup}>
                  <Text style={[styles.helperText, { color: palette.muted }]}>
                    Use this only for manual recovery or non-standard pre-release setup flows.
                  </Text>

                  <Field
                    label="Device setup Wi-Fi name"
                    palette={palette}
                    placeholder="AliceSetup-dev_sensor_hall_01"
                    value={deviceSetupSsid}
                    onChangeText={setDeviceSetupSsid}
                    autoCapitalize="none"
                  />

                  <Field
                    label="Device setup Wi-Fi password"
                    palette={palette}
                    placeholder="alice-setup"
                    value={deviceSetupPassword}
                    onChangeText={setDeviceSetupPassword}
                    secureTextEntry
                  />

                  <Field
                    label="Device setup URL"
                    palette={palette}
                    placeholder="http://192.168.4.1"
                    value={deviceSetupBaseUrl}
                    onChangeText={setDeviceSetupBaseUrl}
                    autoCapitalize="none"
                  />

                  <Text style={[styles.helperText, { color: palette.muted }]}>
                    Hub target:{' '}
                    <Text style={[styles.inlineCode, { color: palette.text }]}>{apiBaseUrl}</Text>
                  </Text>

                  <Text style={[styles.helperText, { color: palette.muted }]}>
                    Claim token:{' '}
                    <Text style={[styles.inlineCode, { color: palette.text }]}>
                      {activeSession.claim_token}
                    </Text>
                  </Text>

                  <Pressable
                    disabled={localProvisioning || deviceApJoining || !activeSession.claim_token}
                    onPress={handleSendToDevice}
                    style={[
                      styles.secondaryActionButton,
                      { borderColor: palette.border, backgroundColor: palette.subtlePanel },
                      (localProvisioning || deviceApJoining || !activeSession.claim_token)
                        ? styles.disabledButton
                        : null,
                    ]}>
                    {localProvisioning && !deviceApJoining ? (
                      <ActivityIndicator color={palette.text} />
                    ) : (
                      <Text style={[styles.secondaryActionButtonText, { color: palette.text }]}>
                        Send setup manually
                      </Text>
                    )}
                  </Pressable>

                  <Text style={[styles.helperText, { color: palette.muted }]}>
                    Current endpoint:{' '}
                    <Text style={[styles.inlineCode, { color: palette.text }]}>
                      {normalizeDeviceSetupBaseUrl(deviceSetupBaseUrl)}/provision
                    </Text>
                  </Text>
                </View>
              ) : null}
            </View>

            <View style={[styles.infoCard, { backgroundColor: palette.subtlePanel, borderColor: palette.border }]}>
              <View style={styles.statusRow}>
                <Text style={[styles.infoLabel, { color: palette.muted }]}>Claim status</Text>
                {polling ? <ActivityIndicator color={palette.primary} size="small" /> : null}
              </View>
              <StatusPill status={sessionStatus?.status ?? activeSession.status} palette={palette} />
              {sessionClaimed ? (
                <>
                  <Text style={[styles.infoLabel, { color: palette.muted }]}>Finish this device</Text>
                  <Text style={[styles.infoValue, { color: palette.text }]}>
                    {requestedDeviceName.trim() || scannedPayload?.model || 'Your device'}
                  </Text>
                  <Text style={[styles.helperText, { color: palette.muted }]}>
                    Room: {selectedRoomName}. You can still adjust the name or room above before
                    opening the device.
                  </Text>
                  {finalizeError ? (
                    <Text style={[styles.errorText, { color: palette.danger }]}>{finalizeError}</Text>
                  ) : null}
                  {finalizeSuccess ? (
                    <Text style={[styles.successText, { color: palette.goodText }]}>{finalizeSuccess}</Text>
                  ) : null}
                  <Pressable
                    disabled={finalizingClaim}
                    onPress={() => void handleFinalizeClaim()}
                    style={[
                      styles.secondaryActionButton,
                      { borderColor: palette.border, backgroundColor: palette.subtlePanel },
                      finalizingClaim ? styles.disabledButton : null,
                    ]}>
                    {finalizingClaim ? (
                      <ActivityIndicator color={palette.text} />
                    ) : (
                      <Text style={[styles.secondaryActionButtonText, { color: palette.text }]}>
                        Save name and room
                      </Text>
                    )}
                  </Pressable>
                  <View
                    style={[
                      styles.infoCard,
                      { backgroundColor: palette.input, borderColor: palette.border },
                    ]}>
                    <Text style={[styles.infoLabel, { color: palette.muted }]}>{"What's ready now"}</Text>
                    {claimedDeviceLoading ? <ActivityIndicator color={palette.primary} /> : null}
                    {claimedDeviceError ? (
                      <Text style={[styles.errorText, { color: palette.danger }]}>{claimedDeviceError}</Text>
                    ) : null}
                    {claimedDeviceDetail ? (
                      <>
                        <Text style={[styles.infoValue, { color: palette.text }]}>
                          {describeClaimedDeviceStatus(claimedDeviceDetail, relayStateOn)}
                        </Text>
                        <Text style={[styles.helperText, { color: palette.muted }]}>
                          {describeClaimedDeviceNextStep(claimedDeviceDetail, sensorEntityLabels)}
                        </Text>
                        <View style={styles.capabilityRow}>
                          {claimedDeviceDetail.entities.length === 0 ? (
                            <Text style={[styles.helperText, { color: palette.muted }]}>
                              Alice is still waiting for this device to publish its capabilities.
                            </Text>
                          ) : (
                            claimedDeviceDetail.entities.map((entity) => (
                              <CapabilityPill
                                key={entity.id}
                                label={formatCapabilityLabel(entity.kind, entity.name)}
                                palette={palette}
                              />
                            ))
                          )}
                        </View>
                        {relayEntity && relayStateOn !== null ? (
                          <Pressable
                            disabled={claimedActionBusy}
                            onPress={() => void handleToggleClaimedRelay()}
                            style={[
                              styles.primaryButton,
                              { backgroundColor: palette.primary },
                              claimedActionBusy ? styles.disabledButton : null,
                            ]}>
                            {claimedActionBusy ? (
                              <ActivityIndicator color={palette.primaryText} />
                            ) : (
                              <Text style={[styles.primaryButtonText, { color: palette.primaryText }]}>
                                {relayStateOn ? 'Turn it off now' : 'Turn it on now'}
                              </Text>
                            )}
                          </Pressable>
                        ) : null}
                      </>
                    ) : claimedDeviceLoading ? null : (
                      <Text style={[styles.helperText, { color: palette.muted }]}>
                        Alice is finishing the first live view for this device.
                      </Text>
                    )}
                  </View>
                  <View style={styles.qrActionRow}>
                    <Pressable
                      onPress={() =>
                        router.push({
                          pathname: '/(tabs)/devices/[deviceId]',
                          params: { deviceId: sessionStatus?.claimed_device_id ?? '' },
                        })
                      }
                      style={[styles.primaryButton, styles.actionButton, { backgroundColor: palette.primary }]}>
                      <Text style={[styles.primaryButtonText, { color: palette.primaryText }]}>
                        {primaryOpenActionLabel}
                      </Text>
                    </Pressable>
                    <Pressable
                      onPress={() => router.push('/(tabs)')}
                      style={[
                        styles.secondaryActionButton,
                        styles.actionButton,
                        { borderColor: palette.border, backgroundColor: palette.subtlePanel },
                      ]}>
                      <Text style={[styles.secondaryActionButtonText, { color: palette.text }]}>
                        Go home
                      </Text>
                    </Pressable>
                    <Pressable
                      onPress={handleReset}
                      style={[
                        styles.secondaryActionButton,
                        styles.actionButton,
                        { borderColor: palette.border, backgroundColor: palette.subtlePanel },
                      ]}>
                      <Text style={[styles.secondaryActionButtonText, { color: palette.text }]}>
                        Add another
                      </Text>
                    </Pressable>
                  </View>
                </>
              ) : (
                <Text style={[styles.helperText, { color: palette.muted }]}>
                  Waiting for the device to complete its side of the claim handshake. Polling may
                  pause briefly while your phone is temporarily connected to the device setup
                  network.
                </Text>
              )}
            </View>
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function Field({
  label,
  palette,
  value,
  onChangeText,
  placeholder,
  autoCapitalize = 'sentences',
  secureTextEntry = false,
}: {
  label: string;
  palette: ReturnType<typeof getMobilePalette>;
  value: string;
  onChangeText: (value: string) => void;
  placeholder: string;
  autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters';
  secureTextEntry?: boolean;
}) {
  return (
    <View style={styles.fieldGroup}>
      <Text style={[styles.fieldLabel, { color: palette.muted }]}>{label}</Text>
      <TextInput
        autoCapitalize={autoCapitalize}
        autoCorrect={false}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={palette.placeholder}
        secureTextEntry={secureTextEntry}
        style={[
          styles.input,
          { backgroundColor: palette.input, borderColor: palette.border, color: palette.text },
        ]}
        value={value}
      />
    </View>
  );
}

function CapabilityPill({
  label,
  palette,
}: {
  label: string;
  palette: ReturnType<typeof getMobilePalette>;
}) {
  return (
    <View
      style={[
        styles.capabilityPill,
        { backgroundColor: palette.subtlePanel, borderColor: palette.border },
      ]}>
      <Text style={[styles.capabilityPillText, { color: palette.text }]}>{label}</Text>
    </View>
  );
}

function formatCapabilityLabel(kind: string, fallbackName: string): string {
  switch (kind) {
    case 'switch.relay':
      return 'Light control';
    case 'sensor.motion':
      return 'Motion';
    case 'sensor.temperature':
      return 'Temperature';
    case 'sensor.illuminance':
      return 'Light level';
    default:
      return fallbackName;
  }
}

function describeClaimedDeviceStatus(
  detail: DeviceDetail,
  relayStateOn: boolean | null,
): string {
  if (detail.entities.some((entity) => entity.kind === 'switch.relay') && relayStateOn !== null) {
    return relayStateOn ? 'The light is on and ready to control.' : 'The light is ready to control.';
  }

  if (detail.entities.some((entity) => entity.kind.startsWith('sensor.'))) {
    return 'The sensor is now attached to this home and ready to report.';
  }

  return 'This device is now attached to this home.';
}

function describeClaimedDeviceNextStep(
  detail: DeviceDetail,
  sensorEntityLabels: string[],
): string {
  if (detail.entities.some((entity) => entity.kind === 'switch.relay')) {
    return 'Test the light once, then open the device page to confirm live state and recent activity.';
  }

  if (sensorEntityLabels.length > 0) {
    return `Open the device page to watch ${sensorEntityLabels.join(', ')} arrive live from this room.`;
  }

  return 'Open the device page to confirm its live state and latest activity.';
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

function StatusPill({
  status,
  palette,
}: {
  status: string;
  palette: ReturnType<typeof getMobilePalette>;
}) {
  const tone =
    status === 'claimed'
      ? { backgroundColor: palette.goodMuted, color: palette.goodText }
      : status === 'expired'
        ? { backgroundColor: palette.warnMuted, color: palette.warnText }
        : { backgroundColor: palette.subtlePanel, color: palette.text };

  return (
    <View style={[styles.statusPill, { backgroundColor: tone.backgroundColor }]}>
      <Text style={[styles.statusPillText, { color: tone.color }]}>{status}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
  screenContent: {
    gap: 16,
    padding: 20,
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
  panel: {
    borderRadius: 24,
    borderWidth: 1,
    gap: 14,
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
  inlineLoader: {
    alignSelf: 'flex-start',
    paddingVertical: 8,
  },
  roomRow: {
    gap: 10,
    paddingVertical: 2,
  },
  qrActionRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  qrActionButton: {
    flexGrow: 1,
  },
  cameraShell: {
    borderRadius: 20,
    borderWidth: 1,
    minHeight: 280,
    overflow: 'hidden',
  },
  cameraView: {
    flex: 1,
  },
  roomChip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  capabilityRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  capabilityPill: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  capabilityPillText: {
    fontSize: 13,
    fontWeight: '700',
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
    borderRadius: 16,
    borderWidth: 1,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  secondaryButtonText: {
    fontSize: 14,
    fontWeight: '700',
  },
  secondaryActionButton: {
    alignItems: 'center',
    borderRadius: 18,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 54,
    paddingHorizontal: 18,
  },
  actionButton: {
    flex: 1,
  },
  secondaryActionButtonText: {
    fontSize: 15,
    fontWeight: '700',
  },
  disabledButton: {
    opacity: 0.6,
  },
  errorText: {
    fontSize: 14,
    lineHeight: 20,
  },
  successText: {
    fontSize: 14,
    lineHeight: 20,
  },
  helperText: {
    fontSize: 14,
    lineHeight: 20,
  },
  sessionHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'space-between',
  },
  sessionHeaderCopy: {
    flex: 1,
    gap: 4,
  },
  infoCard: {
    borderRadius: 20,
    borderWidth: 1,
    gap: 8,
    padding: 14,
  },
  infoLabel: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  infoValue: {
    fontSize: 16,
    fontWeight: '600',
  },
  tokenValue: {
    fontSize: 14,
    fontWeight: '600',
    lineHeight: 20,
  },
  inlineCode: {
    fontFamily: 'monospace',
    fontSize: 13,
    fontWeight: '600',
  },
  statusRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  statusPill: {
    alignSelf: 'flex-start',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  statusPillText: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
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
});
