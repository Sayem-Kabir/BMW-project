"use client";

import { useEffect, useRef, useState } from "react";
import { fleetRiskWebSocketUrl } from "@/lib/api";
import type { FleetRiskWebSocketMessage, RiskScore } from "@/lib/types";

export type FleetRiskSocketStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "disconnected"
  | "error";

interface UseFleetRiskWebSocketOptions {
  orgId?: string;
  enabled?: boolean;
  onRiskUpdate?: (payload: RiskScore) => void;
}

export function useFleetRiskWebSocket({
  orgId,
  enabled = true,
  onRiskUpdate,
}: UseFleetRiskWebSocketOptions = {}) {
  const [status, setStatus] = useState<FleetRiskSocketStatus>("idle");
  const [lastMessage, setLastMessage] = useState<FleetRiskWebSocketMessage | null>(
    null
  );
  const [liveRisk, setLiveRisk] = useState<RiskScore | null>(null);
  const [error, setError] = useState<string | null>(null);
  const callbackRef = useRef(onRiskUpdate);

  useEffect(() => {
    callbackRef.current = onRiskUpdate;
  }, [onRiskUpdate]);

  useEffect(() => {
    if (!enabled) {
      setStatus("idle");
      return undefined;
    }

    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let socket: WebSocket | null = null;

    const connect = () => {
      if (cancelled) return;
      setStatus("connecting");
      setError(null);

      try {
        socket = new WebSocket(fleetRiskWebSocketUrl(orgId));
      } catch (err) {
        setStatus("error");
        setError(err instanceof Error ? err.message : "WebSocket failed");
        return;
      }

      socket.onopen = () => {
        if (cancelled) return;
        setStatus("connected");
      };

      socket.onmessage = (event) => {
        if (cancelled) return;
        try {
          const message = JSON.parse(event.data) as FleetRiskWebSocketMessage;
          setLastMessage(message);
          if (message.type === "risk_update" && message.data) {
            const payload = {
              ...message.data,
              vehicle_id: String(message.data.vehicle_id),
              score: Number(message.data.score ?? message.data.risk_score ?? 0),
              level: (message.data.level ??
                message.data.risk_level ??
                "LOW") as RiskScore["level"],
              risk_score: Number(
                message.data.risk_score ?? message.data.score ?? 0
              ),
              risk_level: (message.data.risk_level ??
                message.data.level ??
                "LOW") as RiskScore["level"],
            };
            setLiveRisk(payload);
            callbackRef.current?.(payload);
          }
        } catch {
          setError("Received invalid WebSocket payload");
        }
      };

      socket.onerror = () => {
        if (cancelled) return;
        setStatus("error");
        setError("Fleet WebSocket connection error");
      };

      socket.onclose = () => {
        if (cancelled) return;
        setStatus("disconnected");
        reconnectTimer = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [enabled, orgId]);

  const sendPing = () => {
    // no-op unless we expose socket; optional for future
  };

  return {
    status,
    error,
    lastMessage,
    liveRisk,
    sendPing,
  };
}
