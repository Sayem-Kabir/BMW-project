"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { analyzeDriverFrame } from "@/lib/api";
import { useDriverStream } from "@/hooks/useDriverStream";
import type { DriverAnalysis, RiskLevel } from "@/lib/types";
import { AlertBanner } from "./AlertBanner";
import { RiskGauge } from "./RiskGauge";

const TARGET_FPS = 4;
const FRAME_INTERVAL_MS = Math.round(1000 / TARGET_FPS);
const JPEG_QUALITY = 0.72;

function riskMessage(a: DriverAnalysis): string {
  const parts: string[] = [];
  if (a.is_drowsy || (a.consecutive_drowsy_frames ?? 0) > 10) parts.push("Drowsiness");
  if (a.is_yawning) parts.push("Yawning");
  if (a.head_pose?.distracted) parts.push("Distracted gaze");
  if (a.phone_detected) parts.push("Phone detected");
  if (a.smoking_detected) parts.push("Smoking detected");
  if (a.yolo_model_loaded && !a.seatbelt_worn) parts.push("Seatbelt not detected");
  if (!parts.length) {
    return a.risk_level === "CRITICAL"
      ? "Critical alertness drop"
      : "Elevated risk — check driver state";
  }
  return parts.join(" · ");
}

function Badge({
  label,
  active,
  danger,
}: {
  label: string;
  active: boolean;
  danger?: boolean;
}) {
  const tone = !active
    ? "border-slate-700 bg-slate-900/70 text-slate-500"
    : danger
      ? "border-red-500/50 bg-red-950/70 text-red-200"
      : "border-emerald-500/40 bg-emerald-950/50 text-emerald-200";
  return (
    <span className={`rounded border px-2.5 py-1 text-xs font-medium ${tone}`}>{label}</span>
  );
}

interface DriverMonitorProps {
  vehicleId?: string;
  sessionId?: string;
}

export function DriverMonitor({ vehicleId, sessionId }: DriverMonitorProps) {
  const ids = useMemo(
    () => ({
      vehicleId: vehicleId || "00000000-0000-4000-8000-000000000001",
      sessionId: sessionId || "00000000-0000-4000-8000-000000000002",
    }),
    [vehicleId, sessionId]
  );

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const sendingRef = useRef(false);

  const [cameraOn, setCameraOn] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [camError, setCamError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [snapshot, setSnapshot] = useState<DriverAnalysis | null>(null);

  const { connect, disconnect, sendFrame, connected, status, error, latest } =
    useDriverStream(ids.vehicleId, ids.sessionId);

  const analysis = latest ?? snapshot;

  const stopCamera = useCallback(() => {
    const video = videoRef.current;
    const stream = video?.srcObject as MediaStream | null;
    stream?.getTracks().forEach((t) => t.stop());
    if (video) video.srcObject = null;
    setCameraOn(false);
    setStreaming(false);
  }, []);

  const startCamera = useCallback(async () => {
    setCamError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraOn(true);
    } catch {
      setCamError("Camera access denied or unavailable. Use file upload instead.");
      setCameraOn(false);
    }
  }, []);

  const captureJpegBlob = useCallback(async (): Promise<Blob | null> => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2) return null;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob), "image/jpeg", JPEG_QUALITY);
    });
  }, []);

  const startStream = useCallback(() => {
    connect();
    setStreaming(true);
    setSnapshot(null);
  }, [connect]);

  const stopStream = useCallback(() => {
    setStreaming(false);
    disconnect();
  }, [disconnect]);

  // Capture loop while streaming
  useEffect(() => {
    if (!streaming || !cameraOn) return;
    const tick = async () => {
      if (sendingRef.current) return;
      if (!connected) return;
      sendingRef.current = true;
      try {
        const blob = await captureJpegBlob();
        if (blob) sendFrame(blob);
      } finally {
        sendingRef.current = false;
      }
    };
    const id = window.setInterval(tick, FRAME_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [streaming, cameraOn, connected, captureJpegBlob, sendFrame]);

  useEffect(() => () => {
    stopStream();
    stopCamera();
  }, [stopStream, stopCamera]);

  const onFileSelected = async (file: File | null) => {
    if (!file) return;
    setBusy(true);
    setCamError(null);
    try {
      const result = await analyzeDriverFrame(file, ids.vehicleId, ids.sessionId, file.name);
      setSnapshot(result);
    } catch (err) {
      setCamError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  };

  const analyzeSnapshot = async () => {
    setBusy(true);
    try {
      const blob = await captureJpegBlob();
      if (!blob) {
        setCamError("No camera frame available");
        return;
      }
      const result = await analyzeDriverFrame(blob, ids.vehicleId, ids.sessionId);
      setSnapshot(result);
    } catch (err) {
      setCamError(err instanceof Error ? err.message : "Snapshot analysis failed");
    } finally {
      setBusy(false);
    }
  };

  const risk: RiskLevel = analysis?.risk_level ?? "LOW";

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <div className="relative overflow-hidden rounded-xl border border-slate-800 bg-slate-950 shadow-2xl shadow-black/40">
        <div className="relative aspect-video bg-slate-900">
          <video
            ref={videoRef}
            className="h-full w-full object-cover"
            playsInline
            muted
            autoPlay
          />
          {!cameraOn && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-gradient-to-br from-slate-900 via-slate-950 to-bmw-blue/30 text-slate-400">
              <p className="text-lg font-medium text-slate-200">Cabin camera offline</p>
              <p className="text-sm">Start the webcam or upload a still frame</p>
            </div>
          )}

          {analysis && (
            <AlertBanner risk={risk} message={riskMessage(analysis)} />
          )}

          <div className="pointer-events-none absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-4 pt-16">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div className="flex flex-wrap gap-2">
                <Badge label="Face" active={Boolean(analysis?.face_detected)} />
                <Badge
                  label="Drowsy"
                  active={Boolean(analysis?.is_drowsy)}
                  danger
                />
                <Badge
                  label="Yawn"
                  active={Boolean(analysis?.is_yawning)}
                  danger
                />
                <Badge
                  label="Phone"
                  active={Boolean(analysis?.phone_detected)}
                  danger
                />
                <Badge
                  label="Smoking"
                  active={Boolean(analysis?.smoking_detected)}
                  danger
                />
                <Badge
                  label="Seatbelt"
                  active={analysis ? Boolean(analysis.seatbelt_worn) : false}
                  danger={Boolean(analysis && !analysis.seatbelt_worn)}
                />
                <Badge
                  label="Distracted"
                  active={Boolean(analysis?.head_pose?.distracted)}
                  danger
                />
              </div>
              {analysis && (
                <RiskGauge score={analysis.alertness_score} risk={risk} />
              )}
            </div>
          </div>
        </div>

        <canvas ref={canvasRef} className="hidden" />

        <div className="flex flex-wrap items-center gap-3 border-t border-slate-800 bg-slate-900/80 px-4 py-3">
          {!cameraOn ? (
            <button
              type="button"
              onClick={startCamera}
              className="rounded-lg bg-bmw-blue px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
            >
              Start camera
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                stopStream();
                stopCamera();
              }}
              className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800"
            >
              Stop camera
            </button>
          )}

          {cameraOn && !streaming && (
            <button
              type="button"
              onClick={startStream}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
            >
              Live stream
            </button>
          )}
          {streaming && (
            <button
              type="button"
              onClick={stopStream}
              className="rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-600"
            >
              Stop stream
            </button>
          )}

          {cameraOn && (
            <button
              type="button"
              disabled={busy}
              onClick={analyzeSnapshot}
              className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50"
            >
              Analyze snapshot
            </button>
          )}

          <button
            type="button"
            disabled={busy}
            onClick={() => fileInputRef.current?.click()}
            className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50"
          >
            Upload frame
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => onFileSelected(e.target.files?.[0] ?? null)}
          />

          <span className="ml-auto text-xs text-slate-400">
            {streaming
              ? connected
                ? status === "ready"
                  ? "Streaming · WS ready"
                  : "Streaming · connecting…"
                : "Streaming · reconnect needed"
              : connected
                ? "WS connected"
                : "Idle"}
            {busy ? " · analyzing…" : ""}
          </span>
        </div>
      </div>

      {(camError || error) && (
        <p className="rounded-lg border border-red-500/40 bg-red-950/40 px-4 py-2 text-sm text-red-200">
          {camError || error}
        </p>
      )}

      {analysis && (
        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="EAR" value={analysis.ear_value.toFixed(3)} />
          <Metric label="MAR" value={analysis.mar_value.toFixed(3)} />
          <Metric
            label="Yaw / Pitch"
            value={`${(analysis.head_pose?.yaw ?? 0).toFixed(1)}° / ${(analysis.head_pose?.pitch ?? 0).toFixed(1)}°`}
          />
          <Metric
            label="Drowsy frames"
            value={String(analysis.consecutive_drowsy_frames ?? 0)}
          />
        </dl>
      )}

      <p className="text-xs text-slate-500">
        Session {ids.sessionId.slice(0, 8)}… · Vehicle {ids.vehicleId.slice(0, 8)}… · ~{TARGET_FPS}{" "}
        fps JPEG over WebSocket
      </p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3">
      <dt className="text-xs uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-100">{value}</dd>
    </div>
  );
}
