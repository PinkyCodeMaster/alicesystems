import { useEffect, useRef } from 'react';

import { authenticateDashboardWebSocket, buildDashboardWebSocketUrl } from '@/lib/alice-api';

type UseDashboardLiveRefreshArgs = {
  apiBaseUrl: string;
  token: string | null;
  enabled: boolean;
  onInvalidate: () => void;
  pollingIntervalMs?: number;
  reconnectDelayMs?: number;
};

export function useDashboardLiveRefresh({
  apiBaseUrl,
  token,
  enabled,
  onInvalidate,
  pollingIntervalMs = 30000,
  reconnectDelayMs = 5000,
}: UseDashboardLiveRefreshArgs) {
  const invalidateRef = useRef(onInvalidate);

  useEffect(() => {
    invalidateRef.current = onInvalidate;
  }, [onInvalidate]);

  useEffect(() => {
    if (!enabled || !token) {
      return;
    }

    let closed = false;
    let socket: WebSocket | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

    const triggerRefresh = () => {
      invalidateRef.current();
    };

    const connect = () => {
      if (closed) {
        return;
      }

      socket = new WebSocket(buildDashboardWebSocketUrl(apiBaseUrl));
      socket.onopen = () => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          authenticateDashboardWebSocket(socket, token);
        }
      };
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(String(event.data)) as { type?: string };
          if (payload.type && payload.type !== 'ping' && payload.type !== 'connected') {
            triggerRefresh();
          }
        } catch {
          triggerRefresh();
        }
      };
      socket.onerror = () => {
        socket?.close();
      };
      socket.onclose = () => {
        if (closed) {
          return;
        }
        reconnectTimeout = setTimeout(connect, reconnectDelayMs);
      };
    };

    connect();
    const interval = setInterval(triggerRefresh, pollingIntervalMs);

    return () => {
      closed = true;
      clearInterval(interval);
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      socket?.close();
    };
  }, [apiBaseUrl, enabled, pollingIntervalMs, reconnectDelayMs, token]);
}
