import { createContext, PropsWithChildren, useContext, useState } from 'react';

import {
  apiRequest,
  loginRequest,
  normalizeApiBaseUrl,
  resolveDefaultApiBaseUrl,
  type User,
} from '@/lib/alice-api';

type LoginArgs = {
  apiBaseUrl: string;
  email: string;
  password: string;
};

type AliceSessionContextValue = {
  apiBaseUrl: string;
  token: string | null;
  user: User | null;
  authenticated: boolean;
  setApiBaseUrl: (value: string) => void;
  hydrateSession: (apiBaseUrl: string, accessToken: string) => Promise<void>;
  login: (args: LoginArgs) => Promise<void>;
  logout: () => void;
};

const AliceSessionContext = createContext<AliceSessionContextValue | null>(null);

export function AliceSessionProvider({ children }: PropsWithChildren) {
  const [apiBaseUrl, setApiBaseUrlState] = useState(resolveDefaultApiBaseUrl);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  const setApiBaseUrl = (value: string) => {
    setApiBaseUrlState(normalizeApiBaseUrl(value));
  };

  const hydrateSession = async (nextApiBaseUrl: string, accessToken: string) => {
    const normalizedApiBaseUrl = normalizeApiBaseUrl(nextApiBaseUrl);
    const nextUser = await apiRequest<User>(
      normalizedApiBaseUrl,
      '/auth/me',
      undefined,
      accessToken,
    );

    setApiBaseUrlState(normalizedApiBaseUrl);
    setToken(accessToken);
    setUser(nextUser);
  };

  const login = async ({ apiBaseUrl: nextApiBaseUrl, email, password }: LoginArgs) => {
    const normalizedApiBaseUrl = normalizeApiBaseUrl(nextApiBaseUrl);
    const auth = await loginRequest(normalizedApiBaseUrl, email, password);
    await hydrateSession(normalizedApiBaseUrl, auth.access_token);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  return (
    <AliceSessionContext.Provider
      value={{
        apiBaseUrl,
        token,
        user,
        authenticated: Boolean(token),
        setApiBaseUrl,
        hydrateSession,
        login,
        logout,
      }}>
      {children}
    </AliceSessionContext.Provider>
  );
}

export function useAliceSession() {
  const context = useContext(AliceSessionContext);
  if (!context) {
    throw new Error('useAliceSession must be used inside AliceSessionProvider');
  }

  return context;
}
