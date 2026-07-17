"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { DriverAnalysis } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type StreamStatus = "idle" | "connecting" | "ready" | "error";

/** Native WebSocket hook: send JPEG frames, receive analysis JSON. */
export function useDriverStream(vehicleId: string, sessionId: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [latest, setLatest] = useState<DriverAnalysis | null>(null);
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<StreamStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const disconnect = useCallback(() => {
    const ws = wsRef.current;
    wsRef.current = null;
    if (ws && ws.readyState <= WebSocket.OPEN) {
      ws.close();
    }
    setConnected(false);
    setStatus("idle");
  }, []);

  const connect = useCallback(() => {
    if (!vehicleId || !sessionId) return;
    disconnect();

    const wsUrl = API_URL.replace(/^http/, "ws");
    const ws = new WebSocket(`${wsUrl}/api/v1/driver/stream/${vehicleId}/${sessionId}`);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;
    setStatus("connecting");
    setError(null);

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onclose = () => {
      setConnected(false);
      setStatus((s) => (s === "error" ? s : "idle"));
      wsRef.current = null;
    };

    ws.onerror = () => {
      setError("WebSocket connection failed — is the backend running?");
      setStatus("error");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(typeof event.data === "string" ? event.data : "");
        if (msg.type === "ready") {
          setStatus("ready");
          return;
        }
        if (msg.type === "error") {
          setError(String(msg.detail || "Stream error"));
          return;
        }
        if (msg.type === "analysis" && msg.payload) {
          setLatest(msg.payload as DriverAnalysis);
          setError(null);
          return;
        }
        // Backward-compatible: bare payload
        if (msg.payload) {
          setLatest(msg.payload as DriverAnalysis);
        }
      } catch {
        /* ignore malformed */
      }
    };
  }, [vehicleId, sessionId, disconnect]);

  const sendFrame = useCallback((data: Blob | ArrayBuffer | Uint8Array) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(data);
    return true;
  }, []);

  useEffect(() => () => disconnect(), [disconnect]);

  return {
    connect,
    disconnect,
    sendFrame,
    connected,
    status,
    error,
    latest,
    setLatest,
  };
}
