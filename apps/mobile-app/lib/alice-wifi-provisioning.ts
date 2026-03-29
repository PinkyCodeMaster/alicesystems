import { requireOptionalNativeModule } from 'expo-modules-core';
import { PermissionsAndroid, Platform, type Permission } from 'react-native';

type AliceWifiProvisioningNativeModule = {
  isAvailableAsync(): Promise<boolean>;
  connectToSetupApAsync(
    ssid: string,
    passphrase?: string | null,
    timeoutMs?: number,
  ): Promise<{
    ssid: string;
    bound: boolean;
  }>;
  releaseWifiBindingAsync(): Promise<boolean>;
  getCurrentLinkStateAsync(): Promise<{
    bound: boolean;
    hasRequestedNetwork: boolean;
  }>;
};

const nativeModule =
  Platform.OS === 'android'
    ? requireOptionalNativeModule<AliceWifiProvisioningNativeModule>('AliceWifiProvisioning')
    : null;

function getRequiredAndroidPermissions(): Permission[] {
  const permissions: Permission[] = [PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION];
  const androidVersion = typeof Platform.Version === 'number' ? Platform.Version : Number.parseInt(Platform.Version, 10);
  if (androidVersion >= 33 && PermissionsAndroid.PERMISSIONS.NEARBY_WIFI_DEVICES) {
    permissions.unshift(PermissionsAndroid.PERMISSIONS.NEARBY_WIFI_DEVICES);
  }
  return permissions;
}

export async function isNativeWifiProvisioningAvailable(): Promise<boolean> {
  if (!nativeModule) {
    return false;
  }
  return nativeModule.isAvailableAsync();
}

export async function ensureWifiProvisioningPermissions(): Promise<void> {
  if (Platform.OS !== 'android') {
    return;
  }

  const requested = await PermissionsAndroid.requestMultiple(getRequiredAndroidPermissions());
  const denied = Object.entries(requested)
    .filter(([, status]) => status !== PermissionsAndroid.RESULTS.GRANTED)
    .map(([permission]) => permission);

  if (denied.length > 0) {
    throw new Error('Wi-Fi setup permissions were denied on this phone.');
  }
}

export async function connectToSetupAccessPoint(
  ssid: string,
  passphrase: string,
  timeoutMs = 30000,
): Promise<{
  ssid: string;
  bound: boolean;
}> {
  if (!nativeModule) {
    throw new Error('Native Wi-Fi setup is not available in this build.');
  }
  return nativeModule.connectToSetupApAsync(ssid, passphrase || null, timeoutMs);
}

export async function releaseSetupAccessPointBinding(): Promise<void> {
  if (!nativeModule) {
    return;
  }
  await nativeModule.releaseWifiBindingAsync();
}
