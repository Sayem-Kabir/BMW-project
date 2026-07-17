"use client";

import { useCallback, useRef, useState } from "react";
import type { DriverAnalysis } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Native WebSocket hook for driver frame streaming (Phase 1). */
export function useDriverStream(vehicleId: string, sessionId: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [latest, setLatest] = useState<DriverAnalysis | null>(null);
  const [connected, setConnected] = useState(false);

  const connect = useCallback(() => {
    const wsUrl = API_URL.replace(/^http/, "ws");
    const ws = new WebSocket(`${wsUrl}/api/v1/driver/stream/${vehicleId}/${sessionId}`);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.payload) setLatest(msg.payload as DriverAnalysis);
      } catch {
        /* ignore malformed */
      }
    };
  }, [vehicleId, sessionId]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  return { connect, disconnect, connected, latest };
}
