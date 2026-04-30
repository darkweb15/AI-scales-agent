"use client";
import { useEffect, useRef, useState, useCallback } from "react";

export type WSEvent = {
  event_type: string;
  payload: any;
};

export function useWebSocket(url: string) {
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null);
  const retryDelay = useRef(1000);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        setConnected(true);
        setReconnecting(false);
        retryDelay.current = 1000;
      };

      ws.current.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as WSEvent;
          setLastEvent(data);
        } catch {}
      };

      ws.current.onclose = () => {
        setConnected(false);
        setReconnecting(true);
        // Exponential backoff: 1s → 2s → 4s → ... → max 30s
        const delay = Math.min(retryDelay.current, 30000);
        retryDelay.current = Math.min(delay * 2, 30000);
        retryTimer.current = setTimeout(connect, delay);
      };

      ws.current.onerror = () => {
        ws.current?.close();
      };
    } catch {
      setReconnecting(true);
    }
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (retryTimer.current) clearTimeout(retryTimer.current);
      ws.current?.close();
    };
  }, [connect]);

  const send = useCallback((msg: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(msg);
    }
  }, []);

  return { connected, reconnecting, lastEvent, send };
}
