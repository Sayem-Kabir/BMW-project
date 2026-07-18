"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { analyzeRoadFrame, resetRoadStream } from "@/lib/api";
import { useRoadStream } from "@/hooks/useRoadStream";
import type { RoadAnalysis, RoadObject } from "@/lib/types";

const TARGET_FPS = 1;
const FRAME_INTERVAL_MS = 1000 / TARGET_FPS;
const JPEG_QUALITY = 0.72;

const BOX_COLORS: Record<string, string> = {
  pedestrian: "#fb7185",
  car: "#38bdf8",
  truck: "#60a5fa",
  bus: "#818cf8",
  bicycle: "#2dd4bf",
  motorcycle: "#34d399",
  "traffic light": "#facc15",
  "traffic sign": "#f97316",
};

interface RoadMonitorProps {
  vehicleId?: string;
}

export function RoadMonitor({ vehicleId }: RoadMonitorProps) {
  const id = useMemo(
    () => vehicleId || "00000000-0000-4000-8000-000000000003",
    [vehicleId]
  );
  const restStreamId = useMemo(() => `road-ui-${id}`, [id]);

  const videoRef = useRef<HTMLVideoElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const waitingForResultRef = useRef(false);

  const [cameraOn, setCameraOn] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<RoadAnalysis | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const {
    connect,
    disconnect,
    sendFrame,
    reset,
    connected,
    status,
    error: streamError,
    latest,
    setLatest,
  } = useRoadStream(id);

  const analysis = latest ?? snapshot;

  const stopCamera = useCallback(() => {
    const video = videoRef.current;
    const stream = video?.srcObject as MediaStream | null;
    stream?.getTracks().forEach((track) => track.stop());
    if (video) video.srcObject = null;
    waitingForResultRef.current = false;
    setCameraOn(false);
    setStreaming(false);
  }, []);

  const startCamera = useCallback(async () => {
    setLocalError(null);
    setSnapshot(null);
    setPreviewUrl(null);
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = media;
        await videoRef.current.play();
      }
      setCameraOn(true);
    } catch {
      setLocalError(
        "Road camera access denied or unavailable. Upload a JPEG/PNG instead."
      );
    }
  }, []);

  const captureJpeg = useCallback(async (): Promise<Blob | null> => {
    const video = videoRef.current;
    const canvas = captureCanvasRef.current;
    if (!video || !canvas || video.readyState < 2) return null;
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const context = canvas.getContext("2d");
    if (!context) return null;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve) => {
      canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY);
    });
  }, []);

  const startStream = useCallback(() => {
    waitingForResultRef.current = false;
    setSnapshot(null);
    setLatest(null);
    connect();
    setStreaming(true);
  }, [connect, setLatest]);

  const stopStream = useCallback(() => {
    waitingForResultRef.current = false;
    setStreaming(false);
    disconnect();
  }, [disconnect]);

  useEffect(() => {
    if (!streaming || !cameraOn || !connected || status !== "ready") return;
    const tick = async () => {
      if (waitingForResultRef.current) return;
      const frame = await captureJpeg();
      if (!frame) return;
      waitingForResultRef.current = sendFrame(frame);
    };
    void tick();
    const interval = window.setInterval(tick, FRAME_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [
    streaming,
    cameraOn,
    connected,
    status,
    captureJpeg,
    sendFrame,
  ]);

  useEffect(() => {
    if (latest || streamError) waitingForResultRef.current = false;
  }, [latest, streamError]);

  useEffect(
    () => () => {
      stopStream();
      stopCamera();
    },
    [stopStream, stopCamera]
  );

  useEffect(
    () => () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    },
    [previewUrl]
  );

  const analyzeBlob = useCallback(
    async (blob: Blob, filename = "road-frame.jpg", resetFirst = false) => {
      setBusy(true);
      setLocalError(null);
      try {
        if (resetFirst) {
          await resetRoadStream(restStreamId).catch(() => false);
        }
        const result = await analyzeRoadFrame(
          blob,
          restStreamId,
          filename
        );
        setSnapshot(result);
        setLatest(null);
      } catch (cause) {
        setLocalError(
          cause instanceof Error ? cause.message : "Road analysis failed"
        );
      } finally {
        setBusy(false);
      }
    },
    [restStreamId, setLatest]
  );

  const onFileSelected = async (file: File | null) => {
    if (!file) return;
    stopStream();
    stopCamera();
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return URL.createObjectURL(file);
    });
    await analyzeBlob(file, file.name, true);
  };

  const analyzeSnapshot = async () => {
    const frame = await captureJpeg();
    if (!frame) {
      setLocalError("No road-camera frame is available");
      return;
    }
    await analyzeBlob(frame);
  };

  const resetAnalysis = useCallback(async () => {
    reset();
    await resetRoadStream(restStreamId).catch(() => false);
    setSnapshot(null);
    setLatest(null);
    setLocalError(null);
  }, [reset, restStreamId, setLatest]);

  const drawOverlay = useCallback(() => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (!width || !height) return;

    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    const context = canvas.getContext("2d");
    if (!context) return;
    context.scale(ratio, ratio);
    context.clearRect(0, 0, width, height);
    if (!analysis) return;

    const shape = analysis.segmentation?.mask_shape;
    const sourceHeight =
      shape?.[0] || videoRef.current?.videoHeight || imageRef.current?.naturalHeight;
    const sourceWidth =
      shape?.[1] || videoRef.current?.videoWidth || imageRef.current?.naturalWidth;
    if (!sourceWidth || !sourceHeight) return;

    const scale = Math.min(width / sourceWidth, height / sourceHeight);
    const renderedWidth = sourceWidth * scale;
    const renderedHeight = sourceHeight * scale;
    const offsetX = (width - renderedWidth) / 2;
    const offsetY = (height - renderedHeight) / 2;

    for (const object of analysis.objects) {
      drawObjectBox(context, object, scale, offsetX, offsetY);
    }

    const temporal = analysis.pedestrian_temporal;
    if (temporal?.detected && temporal.bbox?.length === 4) {
      const [x1, y1, x2, y2] = temporal.bbox;
      context.save();
      context.setLineDash([7, 5]);
      context.lineWidth = 2;
      context.strokeStyle = "#f472b6";
      context.strokeRect(
        offsetX + x1 * scale,
        offsetY + y1 * scale,
        (x2 - x1) * scale,
        (y2 - y1) * scale
      );
      context.restore();
    }
  }, [analysis]);

  useEffect(() => {
    drawOverlay();
    window.addEventListener("resize", drawOverlay);
    return () => window.removeEventListener("resize", drawOverlay);
  }, [drawOverlay]);

  const error = localError || streamError;
  const warnings = analysis?.pipeline?.warnings ?? [];
  const roadRatio = analysis?.segmentation?.class_ratios?.road;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl shadow-black/40">
        <div className="relative aspect-video bg-black">
          <video
            ref={videoRef}
            className={`h-full w-full object-contain ${previewUrl ? "hidden" : ""}`}
            playsInline
            muted
            autoPlay
          />
          {previewUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              ref={imageRef}
              src={previewUrl}
              alt="Uploaded road frame"
              onLoad={drawOverlay}
              className="h-full w-full object-contain"
            />
          )}
          {!cameraOn && !previewUrl && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[radial-gradient(circle_at_center,_rgba(30,64,175,0.22),_transparent_55%)] text-center">
              <div className="rounded-full border border-blue-400/20 bg-blue-500/10 px-4 py-1 text-xs uppercase tracking-[0.3em] text-blue-200">
                ADAS vision
              </div>
              <p className="text-xl font-semibold text-slate-100">
                Road camera offline
              </p>
              <p className="max-w-md text-sm text-slate-400">
                Start the environment-facing camera or upload a road frame.
              </p>
            </div>
          )}
          <canvas
            ref={overlayCanvasRef}
            className="pointer-events-none absolute inset-0 h-full w-full"
          />

          <div className="pointer-events-none absolute left-4 top-4 flex flex-wrap gap-2">
            <StatusPill
              label={`Frame ${analysis?.frame_id ?? "—"}`}
              ready={Boolean(analysis)}
            />
            <StatusPill
              label={`${analysis?.tracking?.active_tracks ?? 0} tracks`}
              ready={Boolean(analysis?.tracking?.tracker_ready)}
            />
            <StatusPill
              label={
                analysis?.depth?.metric_calibrated
                  ? "Metric depth"
                  : "Relative depth"
              }
              ready={Boolean(analysis?.depth?.model_loaded)}
            />
            <StatusPill
              label={`Temporal ${analysis?.pedestrian_temporal?.buffered_frames ?? 0}/${analysis?.pedestrian_temporal?.sequence_length ?? 5}`}
              ready={Boolean(analysis?.pedestrian_temporal?.model_loaded)}
            />
          </div>

          {analysis?.pipeline && (
            <div className="pointer-events-none absolute bottom-4 right-4 rounded-lg border border-slate-700/80 bg-black/70 px-3 py-2 text-right backdrop-blur">
              <p className="text-[10px] uppercase tracking-widest text-slate-400">
                Pipeline
              </p>
              <p className="font-mono text-lg font-semibold text-white">
                {analysis.pipeline.processing_ms.toFixed(0)} ms
              </p>
            </div>
          )}
        </div>

        <canvas ref={captureCanvasRef} className="hidden" />

        <div className="flex flex-wrap items-center gap-3 border-t border-slate-800 bg-slate-900/80 px-4 py-3">
          {!cameraOn ? (
            <button type="button" onClick={startCamera} className="primary-button">
              Start road camera
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                stopStream();
                stopCamera();
              }}
              className="secondary-button"
            >
              Stop camera
            </button>
          )}

          {cameraOn && !streaming && (
            <button type="button" onClick={startStream} className="success-button">
              Start live analysis
            </button>
          )}
          {streaming && (
            <button type="button" onClick={stopStream} className="danger-button">
              Stop live analysis
            </button>
          )}
          {cameraOn && !streaming && (
            <button
              type="button"
              disabled={busy}
              onClick={analyzeSnapshot}
              className="secondary-button"
            >
              Analyze snapshot
            </button>
          )}
          <button
            type="button"
            disabled={busy}
            onClick={() => fileInputRef.current?.click()}
            className="secondary-button"
          >
            Upload frame
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png"
            className="hidden"
            onChange={(event) =>
              void onFileSelected(event.target.files?.[0] ?? null)
            }
          />
          <button type="button" onClick={resetAnalysis} className="ghost-button">
            Reset state
          </button>

          <span className="ml-auto text-xs text-slate-400">
            {streaming
              ? status === "ready"
                ? "Live · awaiting frames"
                : "Connecting…"
              : "Idle"}
            {busy ? " · analyzing…" : ""}
          </span>
        </div>
      </section>

      {error && (
        <p className="rounded-xl border border-red-500/40 bg-red-950/40 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      )}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Metric
          label="Tracked objects"
          value={String(analysis?.tracking?.active_tracks ?? 0)}
        />
        <Metric
          label="Confirmed"
          value={String(analysis?.tracking?.confirmed_tracks ?? 0)}
        />
        <Metric
          label="Road coverage"
          value={roadRatio == null ? "—" : `${(roadRatio * 100).toFixed(1)}%`}
        />
        <Metric
          label="Known lights"
          value={String(analysis?.traffic_lights?.known_count ?? 0)}
        />
        <Metric
          label="Depth inference"
          value={
            analysis?.depth?.inference_ms == null
              ? "—"
              : `${analysis.depth.inference_ms.toFixed(0)} ms`
          }
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.45fr_0.75fr]">
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-blue-300">
                Scene objects
              </p>
              <h2 className="mt-1 text-lg font-semibold">Tracked detections</h2>
            </div>
            <span className="text-xs text-slate-500">
              {analysis?.objects.length ?? 0} visible
            </span>
          </div>
          {!analysis?.objects.length ? (
            <p className="px-5 py-10 text-center text-sm text-slate-500">
              Analyze a frame to populate tracked road objects.
            </p>
          ) : (
            <div className="divide-y divide-slate-800">
              {analysis.objects.map((object) => (
                <ObjectRow key={object.id} object={object} />
              ))}
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <p className="text-xs uppercase tracking-[0.2em] text-blue-300">
            Pipeline health
          </p>
          <div className="mt-4 space-y-3">
            <StageRow
              label="Road segmentation"
              ready={Boolean(analysis?.segmentation?.model_loaded)}
              value={stageTime(analysis, "segmentation")}
            />
            <StageRow
              label="Detection"
              ready={Boolean(analysis?.tracking?.tracker_ready)}
              value={stageTime(analysis, "detection")}
            />
            <StageRow
              label="Tracking"
              ready={Boolean(analysis?.tracking?.tracker_ready)}
              value={stageTime(analysis, "tracking")}
            />
            <StageRow
              label="Depth"
              ready={Boolean(analysis?.depth?.model_loaded)}
              value={stageTime(analysis, "depth")}
            />
            <StageRow
              label="Traffic lights"
              ready={Boolean(analysis?.traffic_lights?.classifier_ready)}
              value={stageTime(analysis, "traffic_lights")}
            />
            <StageRow
              label="Pedestrian temporal"
              ready={Boolean(analysis?.pedestrian_temporal?.model_loaded)}
              value={stageTime(analysis, "pedestrian_temporal")}
            />
          </div>
        </section>
      </div>

      {warnings.length > 0 && (
        <section className="rounded-xl border border-amber-500/30 bg-amber-950/20 px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-widest text-amber-300">
            Pipeline notices
          </p>
          <ul className="mt-2 space-y-1 text-sm text-amber-100/80">
            {warnings.map((warning) => (
              <li key={warning}>• {warning}</li>
            ))}
          </ul>
        </section>
      )}

      <p className="text-xs text-slate-500">
        Vehicle {id.slice(0, 8)}… · {TARGET_FPS} fps binary JPEG over WebSocket ·
        boxes are projected from the analyzed source frame.
      </p>
    </div>
  );
}

function drawObjectBox(
  context: CanvasRenderingContext2D,
  object: RoadObject,
  scale: number,
  offsetX: number,
  offsetY: number
) {
  if (!object.bbox || object.bbox.length !== 4) return;
  const [x1, y1, x2, y2] = object.bbox;
  const left = offsetX + x1 * scale;
  const top = offsetY + y1 * scale;
  const width = (x2 - x1) * scale;
  const height = (y2 - y1) * scale;
  const color = BOX_COLORS[object.class] || "#cbd5e1";
  const details = [
    `${object.class} ${(object.confidence * 100).toFixed(0)}%`,
    object.distance_m == null ? null : `${object.distance_m.toFixed(1)}m`,
    object.state && object.state !== "UNKNOWN" ? object.state : null,
    object.temporally_confirmed ? "temporal" : null,
  ].filter(Boolean);
  const label = details.join(" · ");

  context.lineWidth = object.track_confirmed ? 2.5 : 1.5;
  context.strokeStyle = color;
  context.strokeRect(left, top, width, height);
  context.font = "600 12px ui-monospace, SFMono-Regular, monospace";
  const labelWidth = context.measureText(label).width + 12;
  const labelTop = Math.max(0, top - 23);
  context.fillStyle = "rgba(2, 6, 23, 0.86)";
  context.fillRect(left, labelTop, labelWidth, 22);
  context.fillStyle = color;
  context.fillText(label, left + 6, labelTop + 15);
}

function StatusPill({ label, ready }: { label: string; ready: boolean }) {
  return (
    <span
      className={`rounded-full border px-3 py-1 text-[11px] font-medium backdrop-blur ${
        ready
          ? "border-emerald-400/30 bg-emerald-950/70 text-emerald-200"
          : "border-slate-600/60 bg-slate-950/70 text-slate-400"
      }`}
    >
      {label}
    </span>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3">
      <dt className="text-[10px] uppercase tracking-widest text-slate-500">
        {label}
      </dt>
      <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-100">
        {value}
      </dd>
    </div>
  );
}

function ObjectRow({ object }: { object: RoadObject }) {
  const color = BOX_COLORS[object.class] || "#cbd5e1";
  return (
    <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3 px-5 py-3">
      <span
        className="h-8 w-1 rounded-full"
        style={{ backgroundColor: color }}
      />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium capitalize text-slate-100">
            {object.class}
          </span>
          <span className="font-mono text-xs text-slate-500">{object.id}</span>
          {object.temporally_confirmed && (
            <span className="rounded bg-pink-950 px-1.5 py-0.5 text-[10px] uppercase text-pink-300">
              temporal
            </span>
          )}
          {object.state && object.state !== "UNKNOWN" && (
            <span className="rounded bg-amber-950 px-1.5 py-0.5 text-[10px] uppercase text-amber-300">
              {object.state}
            </span>
          )}
        </div>
        <p className="mt-1 text-xs text-slate-500">
          {(object.confidence * 100).toFixed(1)}% confidence ·{" "}
          {object.track_hits ?? 0} observations
        </p>
      </div>
      <div className="text-right">
        <p className="font-mono text-sm text-slate-200">
          {object.distance_m == null ? "relative" : `${object.distance_m.toFixed(1)} m`}
        </p>
        <p className="text-[10px] uppercase tracking-wider text-slate-500">
          {object.distance_calibrated ? "calibrated" : "depth"}
        </p>
      </div>
    </div>
  );
}

function StageRow({
  label,
  ready,
  value,
}: {
  label: string;
  ready: boolean;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="flex items-center gap-2 text-slate-300">
        <span
          className={`h-2 w-2 rounded-full ${
            ready ? "bg-emerald-400" : "bg-slate-600"
          }`}
        />
        {label}
      </span>
      <span className="font-mono text-xs text-slate-500">{value}</span>
    </div>
  );
}

function stageTime(analysis: RoadAnalysis | null, stage: string): string {
  const value = analysis?.pipeline?.stage_times_ms?.[stage];
  return value == null ? "—" : `${value.toFixed(0)} ms`;
}
