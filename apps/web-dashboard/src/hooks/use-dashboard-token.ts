"use client";

import { useEffect, useState } from "react";

import { TOKEN_KEY } from "@/lib/alice-client";

export function useDashboardToken() {
  const [token, setToken] = useState<string | null>(null);
  const [tokenReady, setTokenReady] = useState(false);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const stored = window.localStorage.getItem(TOKEN_KEY);
      setToken(stored);
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

  return {
    token,
    tokenReady,
    storeToken,
    clearToken,
  };
}
