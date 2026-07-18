"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { RoadAnalysis } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type RoadStreamStatus = "idle" | "connecting" | "ready" | "error";

export function useRoadStream(vehicleId: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [latest, setLatest] = useState<RoadAnalysis | null>(null);
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<RoadStreamStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const disconnect = useCallback(() => {
    const websocket = wsRef.current;
    wsRef.current = null;
    if (websocket && websocket.readyState <= WebSocket.OPEN) {
      websocket.close();
    }
    setConnected(false);
    setStatus("idle");
  }, []);

  const connect = useCallback(() => {
    if (!vehicleId) return;
    disconnect();

    const wsUrl = API_URL.replace(/^http/, "ws");
    const websocket = new WebSocket(
      `${wsUrl}/api/v1/road/stream/${encodeURIComponent(vehicleId)}`
    );
    websocket.binaryType = "arraybuffer";
    wsRef.current = websocket;
    setStatus("connecting");
    setError(null);

    websocket.onopen = () => setConnected(true);
    websocket.onclose = () => {
      setConnected(false);
      setStatus((current) => (current === "error" ? current : "idle"));
      wsRef.current = null;
    };
    websocket.onerror = () => {
      setError("Road WebSocket connection failed — is the backend running?");
      setStatus("error");
    };
    websocket.onmessage = (event) => {
      try {
        const message = JSON.parse(
          typeof event.data === "string" ? event.data : ""
        );
        if (message.type === "ready") {
          setStatus("ready");
          return;
        }
        if (message.type === "reset") {
          setLatest(null);
          return;
        }
        if (message.type === "error") {
          setError(String(message.detail || "Road stream error"));
          return;
        }
        if (message.type === "analysis" && message.payload) {
          setLatest(message.payload as RoadAnalysis);
          setError(null);
        }
      } catch {
        setError("Road stream returned malformed JSON");
      }
    };
  }, [vehicleId, disconnect]);

  const sendFrame = useCallback((data: Blob | ArrayBuffer | Uint8Array) => {
    const websocket = wsRef.current;
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return false;
    websocket.send(data);
    return true;
  }, []);

  const reset = useCallback(() => {
    const websocket = wsRef.current;
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return false;
    websocket.send("reset");
    setLatest(null);
    return true;
  }, []);

  useEffect(() => () => disconnect(), [disconnect]);

  return {
    connect,
    disconnect,
    sendFrame,
    reset,
    connected,
    status,
    error,
    latest,
    setLatest,
  };
}
