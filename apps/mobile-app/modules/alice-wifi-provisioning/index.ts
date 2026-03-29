export type AliceWifiProvisioningModule = {
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

export {};
