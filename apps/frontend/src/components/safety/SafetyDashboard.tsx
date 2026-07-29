"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RiskGauge } from "@/components/driver/RiskGauge";
import { XaiPanel } from "@/components/fleet/XaiPanel";
import { useFleetRiskWebSocket } from "@/hooks/useFleetRiskWebSocket";
import {
  acknowledgeSafetyEvent,
  clipLink,
  computeRisk,
  detectSafetyEvents,
  getCurrentRisk,
  getRiskHistory,
  getSafetyEvents,
} from "@/lib/api";
import type {
  RiskLevel,
  RiskScore,
  SafetyEvent,
} from "@/lib/types";

const DEFAULT_VEHICLE_ID = "00000000-0000-4000-8000-000000000003";
const DEFAULT_DRIVER_ID = "00000000-0000-4000-8000-000000000001";
const DEFAULT_SESSION_ID = "00000000-0000-4000-8000-000000000002";
const DEFAULT_ORG_ID = "00000000-0000-4000-8000-000000000010";

const SEVERITY_CLASSES: Record<RiskLevel, string> = {
  LOW: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  MEDIUM: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  HIGH: "border-orange-500/40 bg-orange-500/10 text-orange-300",
  CRITICAL: "border-red-500/40 bg-red-500/10 text-red-300",
};

type Scenario = {
  id: string;
  label: string;
  description: string;
  icon: string;
  driverState: Record<string, unknown>;
  roadState: Record<string, unknown>;
  telemetry: Record<string, unknown>;
  expectedOutcome: string;
  severity: "safe" | "warning" | "danger" | "critical";
};

const SCENARIOS: Scenario[] = [
  {
    id: "triple-critical",
    label: "Critical Multi-Threat",
    description: "Driver asleep + near collision + pedestrian nearby",
    icon: "🚨",
    severity: "critical",
    driverState: { consecutive_drowsy_frames: 65, ear_value: 0.18, phone_detected: false, seatbelt_worn: false },
    roadState: { objects: [{ class: "car", distance_m: 9.8, relative_speed_kmh: 58, track_id: 1, confirmed: true }, { class: "pedestrian", distance_m: 8.0, relative_speed_kmh: 5.0, track_id: 2, temporally_confirmed: true }] },
    telemetry: { speed_kmh: 72, latitude: 48.1351, longitude: 11.582 },
    expectedOutcome: "Expects 3 safety events",
  },
  {
    id: "unsafe-follow-ped",
    label: "Tailgating + Pedestrian",
    description: "Too close to car ahead, pedestrian on roadside",
    icon: "⚠️",
    severity: "danger",
    driverState: { is_drowsy: false, phone_detected: false, seatbelt_worn: true },
    roadState: { objects: [{ class: "car", distance_m: 50.0, relative_speed_kmh: 60, track_id: 1, confirmed: true }, { class: "pedestrian", distance_m: 10.0, relative_speed_kmh: 4.0, track_id: 2, temporally_confirmed: true }] },
    telemetry: { speed_kmh: 72, latitude: 48.1351, longitude: 11.582 },
    expectedOutcome: "Expects 2 safety events",
  },
  {
    id: "near-collision",
    label: "Near Collision",
    description: "Drowsy driver approaching vehicle rapidly",
    icon: "💥",
    severity: "warning",
    driverState: { is_drowsy: true, ear_value: 0.22, phone_detected: false, seatbelt_worn: false },
    roadState: { objects: [{ class: "car", distance_m: 9.8, relative_speed_kmh: 58, track_id: 1, confirmed: true }] },
    telemetry: { speed_kmh: 58, latitude: 48.1351, longitude: 11.582 },
    expectedOutcome: "Expects 1 safety event",
  },
  {
    id: "safe-drive",
    label: "Safe Driving",
    description: "Normal conditions, no threats detected",
    icon: "✅",
    severity: "safe",
    driverState: { is_drowsy: false, phone_detected: false, seatbelt_worn: true },
    roadState: {},
    telemetry: { speed_kmh: 45, latitude: 48.1351, longitude: 11.582 },
    expectedOutcome: "No events (safe)",
  },
];

function errorMessage(error: unknown): string {
  if (error && typeof error === "object" && "response" in error && error.response && typeof error.response === "object" && "data" in error.response) {
    const data = error.response.data as { detail?: unknown };
    if (data.detail) return String(data.detail);
  }
  return error instanceof Error ? error.message : "Request failed";
}

function SeverityBadge({ severity }: { severity: RiskLevel }) {
  return (
    <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${SEVERITY_CLASSES[severity]}`}>
      {severity}
    </span>
  );
}

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function isPlaceholderRisk(payload: RiskScore | null | undefined): boolean {
  if (!payload) return true;
  return payload.score <= 0 && payload.level === "LOW" && Boolean(payload.message?.toLowerCase().includes("no recent"));
}

function normalizeRisk(payload: unknown): RiskScore {
  const data = (payload ?? {}) as Record<string, unknown>;
  return {
    vehicle_id: String(data.vehicle_id ?? ""),
    score: Number(data.score ?? data.risk_score ?? 0),
    level: String(data.level ?? data.risk_level ?? "LOW") as RiskLevel,
    risk_score: Number(data.risk_score ?? data.score ?? 0),
    risk_level: String(data.risk_level ?? data.level ?? "LOW") as RiskLevel,
    factors: (data.factors as RiskScore["factors"]) ?? [],
    reasons: (data.reasons as string[]) ?? [],
    overrides: (data.overrides as RiskScore["overrides"]) ?? [],
    base_score: data.base_score === undefined || data.base_score === null ? null : Number(data.base_score),
    base_level: (data.base_level as RiskLevel | null) ?? null,
    timestamp: String(data.timestamp ?? new Date().toISOString()),
    method: data.method ? String(data.method) : null,
    phase: data.phase ? String(data.phase) : undefined,
    message: data.message ? String(data.message) : null,
  };
}

function EventCard({ event, driverId, onAcknowledged }: { event: SafetyEvent; driverId: string; onAcknowledged: () => void }) {
  const clip = clipLink(event.video_clip_url);
  const acknowledge = useMutation({
    mutationFn: () => acknowledgeSafetyEvent(event.id, driverId),
    onSuccess: onAcknowledged,
  });

  const typeLabel = event.event_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <article className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 transition-colors hover:border-slate-700">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-white">{typeLabel}</h3>
            <SeverityBadge severity={event.severity} />
            {event.acknowledged && (
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">✓ Acknowledged</span>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-500">{formatTime(event.timestamp)}</p>
        </div>
        {!event.acknowledged && (
          <button
            type="button"
            onClick={() => acknowledge.mutate()}
            disabled={acknowledge.isPending}
            className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {acknowledge.isPending ? "Saving…" : "✓ Acknowledge"}
          </button>
        )}
      </div>

      {event.xai_explanation && (
        <p className="mt-3 rounded-lg bg-slate-800/50 p-3 text-sm leading-relaxed text-slate-300">
          💡 {event.xai_explanation}
        </p>
      )}

      <XaiPanel eventId={event.id} eventType={event.event_type} className="mt-3" autoLabel="View detailed explanation" />

      <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-400">
        {event.telemetry_snapshot?.speed_kmh !== undefined && (
          <span className="rounded bg-slate-800 px-2 py-0.5">🏎️ {String(event.telemetry_snapshot.speed_kmh)} km/h</span>
        )}
        {event.telemetry_snapshot?.ttc_seconds !== undefined && (
          <span className="rounded bg-slate-800 px-2 py-0.5">⏱️ TTC {String(event.telemetry_snapshot.ttc_seconds)}s</span>
        )}
        {event.telemetry_snapshot?.risk_score_at_event !== undefined && (
          <span className="rounded bg-slate-800 px-2 py-0.5">📊 Risk {String(event.telemetry_snapshot.risk_score_at_event)}</span>
        )}
      </div>

      {clip.href ? (
        <a href={clip.href} target="_blank" rel="noreferrer" className="mt-3 inline-block rounded-lg bg-blue-500/10 px-3 py-1.5 text-sm text-blue-300 hover:bg-blue-500/20">
          🎬 Watch clip
        </a>
      ) : (
        <span className="mt-3 inline-block text-sm text-slate-500">{clip.label}</span>
      )}
    </article>
  );
}

const SEVERITY_COLORS = { safe: "border-emerald-500/50 bg-emerald-500/10", warning: "border-amber-500/50 bg-amber-500/10", danger: "border-orange-500/50 bg-orange-500/10", critical: "border-red-500/50 bg-red-500/10" };
const SEVERITY_RING = { safe: "ring-emerald-500/30", warning: "ring-amber-500/30", danger: "ring-orange-500/30", critical: "ring-red-500/30" };

export function SafetyDashboard() {
  const queryClient = useQueryClient();
  const vehicleId = DEFAULT_VEHICLE_ID;
  const driverId = DEFAULT_DRIVER_ID;
  const sessionId = DEFAULT_SESSION_ID;
  const orgId = DEFAULT_ORG_ID;

  const [selectedScenario, setSelectedScenario] = useState<Scenario>(SCENARIOS[2]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [manualRisk, setManualRisk] = useState<RiskScore | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { status: wsStatus, error: wsError, liveRisk } = useFleetRiskWebSocket({
    orgId,
    enabled: true,
    onRiskUpdate: (payload) => {
      if (payload.vehicle_id === vehicleId) {
        queryClient.invalidateQueries({ queryKey: ["risk-history", vehicleId] });
      }
    },
  });

  const currentRiskQuery = useQuery({
    queryKey: ["risk-current", vehicleId],
    queryFn: () => getCurrentRisk(vehicleId),
    refetchInterval: 5_000,
  });

  const historyQuery = useQuery({
    queryKey: ["risk-history", vehicleId],
    queryFn: () => getRiskHistory(vehicleId, 40),
  });

  const eventsQuery = useQuery({
    queryKey: ["safety-events", vehicleId],
    queryFn: () => getSafetyEvents(vehicleId, { limit: 50 }),
    refetchInterval: 15_000,
  });

  const displayedRisk = useMemo(() => {
    const liveForVehicle = liveRisk && liveRisk.vehicle_id === vehicleId ? liveRisk : null;
    if (liveForVehicle) return liveForVehicle;
    if (manualRisk) return manualRisk;
    const currentFromApi = currentRiskQuery.data ? normalizeRisk(currentRiskQuery.data) : null;
    if (currentFromApi && !isPlaceholderRisk(currentFromApi)) return currentFromApi;
    const latestHistory = historyQuery.data?.history?.[0];
    if (latestHistory) return normalizeRisk({ ...latestHistory, vehicle_id: vehicleId });
    return currentFromApi;
  }, [liveRisk, manualRisk, currentRiskQuery.data, historyQuery.data, vehicleId]);

  const historyChartData = useMemo(() => {
    const rows = historyQuery.data?.history ?? [];
    return [...rows].reverse().map((item) => ({ time: formatTime(item.timestamp), score: item.score }));
  }, [historyQuery.data]);

  const computeMutation = useMutation({
    mutationFn: async () => {
      setActionError(null);
      return computeRisk(vehicleId, {
        driver_state: selectedScenario.driverState,
        road_state: selectedScenario.roadState,
        telemetry: selectedScenario.telemetry,
        publish: true,
        cache: true,
        persist: true,
      });
    },
    onSuccess: (payload) => {
      setManualRisk(normalizeRisk(payload));
      queryClient.invalidateQueries({ queryKey: ["risk-current", vehicleId] });
      queryClient.invalidateQueries({ queryKey: ["risk-history", vehicleId] });
    },
    onError: (error) => setActionError(errorMessage(error)),
  });

  const detectMutation = useMutation({
    mutationFn: async () => {
      setActionError(null);
      const riskScore = displayedRisk?.score;
      return detectSafetyEvents(vehicleId, {
        driver_id: driverId,
        session_id: sessionId,
        driver_state: selectedScenario.driverState,
        road_state: selectedScenario.roadState,
        telemetry: selectedScenario.telemetry,
        risk_score: riskScore,
        attach_clips: true,
        enqueue_clip_retry: false,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["safety-events", vehicleId] });
    },
    onError: (error) => setActionError(errorMessage(error)),
  });

  const events = eventsQuery.data?.events ?? [];
  const unacknowledged = events.filter((event) => !event.acknowledged).length;

  return (
    <div className="space-y-8">
      {/* Risk Overview */}
      <div className="grid gap-6 xl:grid-cols-[320px_1fr]">
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Live Risk Score</h2>
            <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${wsStatus === "connected" ? "bg-emerald-500/15 text-emerald-300" : wsStatus === "connecting" ? "bg-amber-500/15 text-amber-300" : "bg-slate-800 text-slate-400"}`}>
              {wsStatus === "connected" ? "● Live" : wsStatus === "connecting" ? "● Connecting" : "○ Offline"}
            </span>
          </div>

          {displayedRisk ? (
            <div className="flex flex-col items-center gap-4">
              <RiskGauge score={Math.round(displayedRisk.score)} risk={displayedRisk.level} />
              <p className="text-sm text-slate-400">Updated {formatTime(displayedRisk.timestamp)}</p>
              {displayedRisk.message && <p className="text-xs text-amber-300">{displayedRisk.message}</p>}
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-slate-400">
              No risk data yet. Select a scenario and run a simulation below.
            </p>
          )}

          {displayedRisk?.reasons?.length ? (
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-semibold text-slate-300">Risk factors</h3>
              <ul className="space-y-1 text-sm text-slate-400">
                {displayedRisk.reasons.map((reason) => <li key={reason}>• {reason}</li>)}
              </ul>
            </div>
          ) : null}

          {wsError && <p className="mt-3 text-xs text-amber-300">{wsError}</p>}
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="mb-2 text-lg font-semibold">Risk History</h2>
          <p className="mb-4 text-sm text-slate-400">Score over time (higher = more dangerous)</p>
          {historyChartData.length > 0 ? (
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyChartData}>
                  <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                  <XAxis dataKey="time" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                  <Line type="monotone" dataKey="score" stroke="#f97316" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="py-12 text-center text-sm text-slate-500">
              No history yet. Run a simulation to see risk scores plotted here.
            </p>
          )}
        </section>
      </div>

      {/* Simulation Panel — user-friendly */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="mb-6">
          <h2 className="text-lg font-semibold">Simulate a Driving Scenario</h2>
          <p className="text-sm text-slate-400">
            Pick a situation to test how the safety system responds
          </p>
        </div>

        <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {SCENARIOS.map((scenario) => (
            <button
              key={scenario.id}
              type="button"
              onClick={() => { setSelectedScenario(scenario); setActionError(null); }}
              className={`rounded-xl border p-4 text-left transition-all ${
                selectedScenario.id === scenario.id
                  ? `${SEVERITY_COLORS[scenario.severity]} ring-2 ${SEVERITY_RING[scenario.severity]}`
                  : "border-slate-700 hover:border-slate-600 hover:bg-slate-800/50"
              }`}
            >
              <span className="text-2xl">{scenario.icon}</span>
              <h3 className="mt-2 text-sm font-semibold text-white">{scenario.label}</h3>
              <p className="mt-1 text-xs text-slate-400">{scenario.description}</p>
            </button>
          ))}
        </div>

        {/* Selected scenario summary */}
        <div className="mb-6 rounded-xl border border-slate-700 bg-slate-800/50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-white">
                <span className="mr-2">{selectedScenario.icon}</span>
                {selectedScenario.label}
              </p>
              <p className="mt-1 text-xs text-slate-400">{selectedScenario.expectedOutcome}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => computeMutation.mutate()}
                disabled={computeMutation.isPending}
                className="rounded-lg bg-orange-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-orange-900/20 hover:bg-orange-500 disabled:opacity-50"
              >
                {computeMutation.isPending ? "Computing…" : "⚡ Compute Risk"}
              </button>
              <button
                type="button"
                onClick={() => detectMutation.mutate()}
                disabled={detectMutation.isPending}
                className="rounded-lg bg-rose-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-rose-900/20 hover:bg-rose-500 disabled:opacity-50"
              >
                {detectMutation.isPending ? "Detecting…" : "🔍 Detect Events"}
              </button>
            </div>
          </div>

          {/* Visual summary of scenario parameters */}
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-slate-900/60 p-3">
              <p className="mb-1 text-xs font-medium text-slate-500">Driver Status</p>
              <div className="flex flex-wrap gap-1.5">
                {selectedScenario.driverState.is_drowsy || (selectedScenario.driverState.consecutive_drowsy_frames as number) > 30 ? (
                  <span className="rounded bg-red-500/20 px-2 py-0.5 text-xs text-red-300">😴 Drowsy</span>
                ) : (
                  <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-xs text-emerald-300">👁️ Alert</span>
                )}
                {selectedScenario.driverState.phone_detected ? (
                  <span className="rounded bg-red-500/20 px-2 py-0.5 text-xs text-red-300">📱 Phone</span>
                ) : null}
                {selectedScenario.driverState.seatbelt_worn ? (
                  <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-xs text-emerald-300">🔒 Belted</span>
                ) : (
                  <span className="rounded bg-amber-500/20 px-2 py-0.5 text-xs text-amber-300">⚠️ No belt</span>
                )}
              </div>
            </div>
            <div className="rounded-lg bg-slate-900/60 p-3">
              <p className="mb-1 text-xs font-medium text-slate-500">Road Objects</p>
              {(selectedScenario.roadState.objects as Array<{ class: string; distance_m: number }> | undefined)?.length ? (
                <div className="flex flex-wrap gap-1.5">
                  {(selectedScenario.roadState.objects as Array<{ class: string; distance_m: number }>).map((obj, i) => (
                    <span key={i} className="rounded bg-blue-500/20 px-2 py-0.5 text-xs text-blue-300">
                      {obj.class === "car" ? "🚗" : obj.class === "pedestrian" ? "🚶" : "🔷"} {obj.class} @ {obj.distance_m}m
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-xs text-slate-500">Clear road</span>
              )}
            </div>
            <div className="rounded-lg bg-slate-900/60 p-3">
              <p className="mb-1 text-xs font-medium text-slate-500">Vehicle</p>
              <span className="rounded bg-sky-500/20 px-2 py-0.5 text-xs text-sky-300">
                🏎️ {String(selectedScenario.telemetry.speed_kmh)} km/h
              </span>
            </div>
          </div>
        </div>

        {/* Results */}
        {actionError && (
          <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            ❌ {actionError}
          </div>
        )}

        {detectMutation.data && (
          <div className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3">
            <p className="text-sm font-semibold text-emerald-300">
              ✓ Detection complete: {detectMutation.data.detected} event{detectMutation.data.detected !== 1 ? "s" : ""} found, {detectMutation.data.persisted} saved
            </p>
            {detectMutation.data.events.length > 0 ? (
              <ul className="mt-2 space-y-1">
                {detectMutation.data.events.map((event) => (
                  <li key={event.id} className="flex items-center gap-2 text-sm text-slate-300">
                    <SeverityBadge severity={event.severity} />
                    <span>{event.event_type.replace(/_/g, " ")}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-1 text-xs text-slate-400">
                All clear — no safety threats detected in this scenario.
              </p>
            )}
          </div>
        )}

        {/* Advanced toggle for devs */}
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-xs text-slate-500 hover:text-slate-300"
        >
          {showAdvanced ? "▾ Hide" : "▸ Show"} raw JSON (for developers)
        </button>
        {showAdvanced && (
          <div className="mt-3 grid gap-3 lg:grid-cols-3">
            <div>
              <p className="mb-1 text-xs text-slate-500">driver_state</p>
              <pre className="max-h-40 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-300">
                {JSON.stringify(selectedScenario.driverState, null, 2)}
              </pre>
            </div>
            <div>
              <p className="mb-1 text-xs text-slate-500">road_state</p>
              <pre className="max-h-40 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-300">
                {JSON.stringify(selectedScenario.roadState, null, 2)}
              </pre>
            </div>
            <div>
              <p className="mb-1 text-xs text-slate-500">telemetry</p>
              <pre className="max-h-40 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-300">
                {JSON.stringify(selectedScenario.telemetry, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </section>

      {/* Safety Events Feed */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Safety Events</h2>
            <p className="text-sm text-slate-400">
              {events.length} total · {unacknowledged > 0 && (
                <span className="text-amber-300">{unacknowledged} need attention</span>
              )}
              {unacknowledged === 0 && "all clear"}
            </p>
          </div>
          <button
            type="button"
            onClick={() => queryClient.invalidateQueries({ queryKey: ["safety-events", vehicleId] })}
            className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-semibold hover:bg-slate-800"
          >
            ↻ Refresh
          </button>
        </div>

        {eventsQuery.data?.warning && <p className="mb-4 text-sm text-amber-300">{eventsQuery.data.warning}</p>}

        {events.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-700 py-12 text-center">
            <p className="text-3xl">🛡️</p>
            <p className="mt-2 text-sm text-slate-400">No safety events yet</p>
            <p className="mt-1 text-xs text-slate-500">Select a scenario above and click "Detect Events" to simulate</p>
          </div>
        ) : (
          <div className="space-y-4">
            {events.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                driverId={driverId}
                onAcknowledged={() => queryClient.invalidateQueries({ queryKey: ["safety-events", vehicleId] })}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
