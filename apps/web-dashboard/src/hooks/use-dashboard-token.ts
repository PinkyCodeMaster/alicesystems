"use client";

import { useEffect, useState } from "react";

import { HUB_SETUP_MEMORY_KEY, TOKEN_KEY } from "@/lib/alice-client";

export function useDashboardToken() {
  const [token, setToken] = useState<string | null>(null);
  const [tokenReady, setTokenReady] = useState(false);
  const [hubSetupRemembered, setHubSetupRemembered] = useState(false);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const stored = window.localStorage.getItem(TOKEN_KEY);
      const hubSetupStored = window.localStorage.getItem(HUB_SETUP_MEMORY_KEY);
      setToken(stored);
      setHubSetupRemembered(hubSetupStored === "true");
      setTokenReady(true);
    }, 0);

    return () => window.clearTimeout(timeout);
  }, []);

  const storeToken = (value: string) => {
    window.localStorage.setItem(TOKEN_KEY, value);
    setToken(value);
  };

  const clearToken = () => {
    window.localStorage.removeItem(TOKEN_KEY);
    setToken(null);
  };

  const rememberHubSetup = (value: boolean) => {
    if (value) {
      window.localStorage.setItem(HUB_SETUP_MEMORY_KEY, "true");
    } else {
      window.localStorage.removeItem(HUB_SETUP_MEMORY_KEY);
    }
    setHubSetupRemembered(value);
  };

  return {
    token,
    tokenReady,
    hubSetupRemembered,
    storeToken,
    clearToken,
    rememberHubSetup,
  };
}
