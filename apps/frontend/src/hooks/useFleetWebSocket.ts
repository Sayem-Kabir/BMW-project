"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  fleetRiskWebSocketUrl,
  getFleetAlerts,
  getFleetOverviewDetail,
} from "@/lib/api";
import type {
  FleetAlert,
  FleetOverview,
  FleetRiskWebSocketMessage,
  FleetVehicleCard,
  RiskScore,
} from "@/lib/types";
import { useAppStore } from "@/lib/store";

export type FleetSocketStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "disconnected"
  | "error";

const DEFAULT_ORG = "00000000-0000-4000-8000-000000000010";

interface Options {
  orgId?: string;
  enabled?: boolean;
  onRiskUpdate?: (payload: RiskScore) => void;
  onSafetyEvent?: (alert: FleetAlert) => void;
}

export function useFleetWebSocket({
  orgId = DEFAULT_ORG,
  enabled = true,
  onRiskUpdate,
  onSafetyEvent,
}: Options = {}) {
  const setFleetOverview = useAppStore((s) => s.setFleetOverview);
  const [status, setStatus] = useState<FleetSocketStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [vehicles, setVehicles] = useState<FleetVehicleCard[]>([]);
  const [alerts, setAlerts] = useState<FleetAlert[]>([]);
  const [overview, setOverview] = useState<FleetOverview | null>(null);
  const [liveRiskByVehicle, setLiveRiskByVehicle] = useState<
    Record<string, RiskScore>
  >({});
  const riskCb = useRef(onRiskUpdate);
  const eventCb = useRef(onSafetyEvent);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    riskCb.current = onRiskUpdate;
  }, [onRiskUpdate]);
  useEffect(() => {
    eventCb.current = onSafetyEvent;
  }, [onSafetyEvent]);

  const refresh = useCallback(async () => {
    try {
      const [detail, alertPayload] = await Promise.all([
        getFleetOverviewDetail(orgId),
        getFleetAlerts(orgId, 50).catch(() => ({ alerts: [] as FleetAlert[] })),
      ]);
      const ov: FleetOverview = {
        vehicle_count: detail.vehicle_count,
        active_alerts: detail.active_alerts,
        average_risk: detail.average_risk,
        online_vehicles: detail.online_vehicles,
        risk_distribution: detail.risk_distribution,
        phase: detail.phase,
      };
      setOverview(ov);
      setFleetOverview(ov);
      setVehicles(detail.vehicles || []);
      setAlerts(alertPayload.alerts || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fleet overview failed");
    }
  }, [orgId, setFleetOverview]);

  useEffect(() => {
    if (!enabled) return undefined;
    void refresh();
    const id = setInterval(() => void refresh(), 30000);
    return () => clearInterval(id);
  }, [enabled, refresh]);

  useEffect(() => {
    if (!enabled) {
      setStatus("idle");
      return undefined;
    }

    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;
      setStatus("connecting");
      setError(null);
      let socket: WebSocket;
      try {
        socket = new WebSocket(fleetRiskWebSocketUrl(orgId));
      } catch (err) {
        setStatus("error");
        setError(err instanceof Error ? err.message : "WebSocket failed");
        return;
      }
      socketRef.current = socket;

      socket.onopen = () => {
        if (!cancelled) setStatus("connected");
      };

      socket.onmessage = (event) => {
        if (cancelled) return;
        try {
          const message = JSON.parse(event.data) as FleetRiskWebSocketMessage;
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
            } as RiskScore;
            setLiveRiskByVehicle((prev) => ({
              ...prev,
              [payload.vehicle_id]: payload,
            }));
            setVehicles((prev) =>
              prev.map((v) =>
                v.id === payload.vehicle_id
                  ? {
                      ...v,
                      risk_score: payload.score,
                      risk_level: payload.level,
                      status:
                        payload.level === "HIGH" || payload.level === "CRITICAL"
                          ? "critical"
                          : payload.level === "MEDIUM"
                            ? "maintenance"
                            : v.status === "critical"
                              ? "operational"
                              : v.status,
                    }
                  : v
              )
            );
            riskCb.current?.(payload);
          } else if (message.type === "safety_event" && message.data) {
            const alert = {
              id: String(message.data.id ?? `${Date.now()}`),
              vehicle_id: String(message.data.vehicle_id ?? ""),
              event_type: String(message.data.event_type ?? "event"),
              severity: String(message.data.severity ?? "MEDIUM"),
              timestamp: String(message.data.timestamp ?? ""),
              video_clip_url: (message.data.video_clip_url as string) || null,
              xai_explanation: (message.data.xai_explanation as string) || null,
              acknowledged: Boolean(message.data.acknowledged),
            } as FleetAlert;
            setAlerts((prev) => [alert, ...prev].slice(0, 50));
            eventCb.current?.(alert);
            void refresh();
          } else if (message.type === "maintenance_alert") {
            void refresh();
          }
        } catch {
          setError("Invalid WebSocket payload");
        }
      };

      socket.onerror = () => {
        if (!cancelled) {
          setStatus("error");
          setError("Fleet WebSocket connection error");
        }
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
      socketRef.current?.close();
    };
  }, [enabled, orgId, refresh]);

  const sendPing = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send("ping");
    }
  };

  return {
    status,
    error,
    connected: status === "connected",
    overview,
    vehicles,
    alerts,
    liveRiskByVehicle,
    refresh,
    sendPing,
  };
}
