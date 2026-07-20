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

const DEMO_DRIVER_STATE = `{
  "is_drowsy": true,
  "ear_value": 0.22,
  "phone_detected": false,
  "seatbelt_worn": false
}`;

const DEMO_ROAD_STATE = `{
  "objects": [
    {
      "class": "car",
      "distance_m": 9.8,
      "relative_speed_kmh": 58,
      "track_id": 1,
      "confirmed": true
    }
  ]
}`;

const DEMO_TELEMETRY = `{
  "speed_kmh": 58,
  "latitude": 48.1351,
  "longitude": 11.5820
}`;

type DemoScenario = {
  id: string;
  label: string;
  hint: string;
  driverState: string;
  roadState: string;
  telemetry: string;
  expectedEvents: string;
};

const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "triple-critical",
    label: "3 events — critical stack",
    hint: "NEAR_COLLISION + DRIVER_ASLEEP + PEDESTRIAN_PROXIMITY_HAZARD",
    driverState: `{
  "consecutive_drowsy_frames": 65,
  "ear_value": 0.18,
  "phone_detected": false,
  "seatbelt_worn": false
}`,
    roadState: `{
  "objects": [
    {
      "class": "car",
      "distance_m": 9.8,
      "relative_speed_kmh": 58,
      "track_id": 1,
      "confirmed": true
    },
    {
      "class": "pedestrian",
      "distance_m": 8.0,
      "relative_speed_kmh": 5.0,
      "track_id": 2,
      "temporally_confirmed": true
    }
  ]
}`,
    telemetry: `{
  "speed_kmh": 72,
  "latitude": 48.1351,
  "longitude": 11.5820
}`,
    expectedEvents: "3 detected, 3 persisted",
  },
  {
    id: "unsafe-follow-ped",
    label: "2 events — following + pedestrian",
    hint: "UNSAFE_FOLLOWING_DISTANCE + PEDESTRIAN_PROXIMITY_HAZARD",
    driverState: `{
  "is_drowsy": false,
  "phone_detected": false,
  "seatbelt_worn": true
}`,
    roadState: `{
  "objects": [
    {
      "class": "car",
      "distance_m": 50.0,
      "relative_speed_kmh": 60,
      "track_id": 1,
      "confirmed": true
    },
    {
      "class": "pedestrian",
      "distance_m": 10.0,
      "relative_speed_kmh": 4.0,
      "track_id": 2,
      "temporally_confirmed": true
    }
  ]
}`,
    telemetry: `{
  "speed_kmh": 72,
  "latitude": 48.1351,
  "longitude": 11.5820
}`,
    expectedEvents: "2 detected, 2 persisted",
  },
  {
    id: "near-collision",
    label: "1 event — near collision",
    hint: "NEAR_COLLISION (TTC < 2s)",
    driverState: DEMO_DRIVER_STATE,
    roadState: DEMO_ROAD_STATE,
    telemetry: DEMO_TELEMETRY,
    expectedEvents: "1 detected, 1 persisted",
  },
  {
    id: "no-events",
    label: "0 events — why you saw zero",
    hint: "is_drowsy alone does not fire DRIVER_ASLEEP (needs 60+ frames or road objects)",
    driverState: `{
  "is_drowsy": true,
  "ear_value": 0.22,
  "phone_detected": false
}`,
    roadState: `{}`,
    telemetry: DEMO_TELEMETRY,
    expectedEvents: "0 detected (intentional demo of empty result)",
  },
];

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function errorMessage(error: unknown): string {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    "data" in error.response
  ) {
    const data = error.response.data as { detail?: unknown };
    if (data.detail) return String(data.detail);
  }
  return error instanceof Error ? error.message : "Request failed";
}

function parseJsonInput(raw: string, label: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error(`${label} must be a JSON object`);
    }
    return parsed as Record<string, unknown>;
  } catch (err) {
    throw new Error(
      err instanceof Error ? err.message : `${label} JSON is invalid`
    );
  }
}

function SeverityBadge({ severity }: { severity: RiskLevel }) {
  return (
    <span
      className={`rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${SEVERITY_CLASSES[severity]}`}
    >
      {severity}
    </span>
  );
}

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
}

function isPlaceholderRisk(payload: RiskScore | null | undefined): boolean {
  if (!payload) return true;
  return (
    payload.score <= 0 &&
    payload.level === "LOW" &&
    Boolean(payload.message?.toLowerCase().includes("no recent"))
  );
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
    base_score:
      data.base_score === undefined || data.base_score === null
        ? null
        : Number(data.base_score),
    base_level: (data.base_level as RiskLevel | null) ?? null,
    timestamp: String(data.timestamp ?? new Date().toISOString()),
    method: data.method ? String(data.method) : null,
    phase: data.phase ? String(data.phase) : undefined,
    message: data.message ? String(data.message) : null,
  };
}

function EventCard({
  event,
  driverId,
  onAcknowledged,
}: {
  event: SafetyEvent;
  driverId: string;
  onAcknowledged: () => void;
}) {
  const clip = clipLink(event.video_clip_url);
  const acknowledge = useMutation({
    mutationFn: () => acknowledgeSafetyEvent(event.id, driverId),
    onSuccess: onAcknowledged,
  });

  return (
    <article className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-white">{event.event_type}</h3>
            <SeverityBadge severity={event.severity} />
            {event.acknowledged ? (
              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                Acknowledged
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-slate-500">{formatTime(event.timestamp)}</p>
        </div>
        {!event.acknowledged ? (
          <button
            type="button"
            onClick={() => acknowledge.mutate()}
            disabled={acknowledge.isPending}
            className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {acknowledge.isPending ? "Saving…" : "Acknowledge"}
          </button>
        ) : null}
      </div>

      {event.xai_explanation ? (
        <p className="mt-3 text-sm leading-relaxed text-slate-300">
          {event.xai_explanation}
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-400">
        {event.telemetry_snapshot?.speed_kmh !== undefined ? (
          <span>Speed: {String(event.telemetry_snapshot.speed_kmh)} km/h</span>
        ) : null}
        {event.telemetry_snapshot?.ttc_seconds !== undefined ? (
          <span>TTC: {String(event.telemetry_snapshot.ttc_seconds)} s</span>
        ) : null}
        {event.telemetry_snapshot?.risk_score_at_event !== undefined ? (
          <span>
            Risk at event: {String(event.telemetry_snapshot.risk_score_at_event)}
          </span>
        ) : null}
      </div>

      <div className="mt-3">
        {clip.href ? (
          <a
            href={clip.href}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-blue-300 underline-offset-2 hover:underline"
          >
            Open video clip
          </a>
        ) : (
          <span className="text-sm text-slate-500">{clip.label}</span>
        )}
      </div>
    </article>
  );
}

export function SafetyDashboard() {
  const queryClient = useQueryClient();
  const [vehicleId, setVehicleId] = useState(DEFAULT_VEHICLE_ID);
  const [driverId, setDriverId] = useState(DEFAULT_DRIVER_ID);
  const [sessionId, setSessionId] = useState(DEFAULT_SESSION_ID);
  const [orgId, setOrgId] = useState(DEFAULT_ORG_ID);
  const [driverStateJson, setDriverStateJson] = useState(DEMO_DRIVER_STATE);
  const [roadStateJson, setRoadStateJson] = useState(DEMO_ROAD_STATE);
  const [telemetryJson, setTelemetryJson] = useState(DEMO_TELEMETRY);
  const [activeScenario, setActiveScenario] = useState("near-collision");
  const [actionError, setActionError] = useState<string | null>(null);
  const [manualRisk, setManualRisk] = useState<RiskScore | null>(null);

  const applyScenario = (scenarioId: string) => {
    const scenario = DEMO_SCENARIOS.find((item) => item.id === scenarioId);
    if (!scenario) return;
    setActiveScenario(scenario.id);
    setDriverStateJson(scenario.driverState);
    setRoadStateJson(scenario.roadState);
    setTelemetryJson(scenario.telemetry);
    setActionError(null);
  };
  const vehicleValid = UUID_PATTERN.test(vehicleId.trim());
  const driverValid = UUID_PATTERN.test(driverId.trim());

  const { status: wsStatus, error: wsError, liveRisk } = useFleetRiskWebSocket({
    orgId: orgId.trim() || DEFAULT_ORG_ID,
    enabled: Boolean(orgId.trim()),
    onRiskUpdate: (payload) => {
      if (payload.vehicle_id === vehicleId.trim()) {
        queryClient.invalidateQueries({ queryKey: ["risk-history", vehicleId] });
      }
    },
  });

  const currentRiskQuery = useQuery({
    queryKey: ["risk-current", vehicleId],
    queryFn: () => getCurrentRisk(vehicleId.trim()),
    enabled: vehicleValid,
    refetchInterval: 5_000,
  });

  const historyQuery = useQuery({
    queryKey: ["risk-history", vehicleId],
    queryFn: () => getRiskHistory(vehicleId.trim(), 40),
    enabled: vehicleValid,
  });

  const eventsQuery = useQuery({
    queryKey: ["safety-events", vehicleId],
    queryFn: () => getSafetyEvents(vehicleId.trim(), { limit: 50 }),
    enabled: vehicleValid,
    refetchInterval: 15_000,
  });

  const displayedRisk = useMemo(() => {
    const liveForVehicle =
      liveRisk && liveRisk.vehicle_id === vehicleId.trim() ? liveRisk : null;
    if (liveForVehicle) return liveForVehicle;
    if (manualRisk) return manualRisk;

    const currentFromApi = currentRiskQuery.data
      ? normalizeRisk(currentRiskQuery.data)
      : null;
    if (currentFromApi && !isPlaceholderRisk(currentFromApi)) {
      return currentFromApi;
    }

    const latestHistory = historyQuery.data?.history?.[0];
    if (latestHistory) {
      return normalizeRisk({
        ...latestHistory,
        vehicle_id: vehicleId.trim(),
      });
    }

    return currentFromApi;
  }, [
    liveRisk,
    manualRisk,
    currentRiskQuery.data,
    historyQuery.data,
    vehicleId,
  ]);

  const historyChartData = useMemo(() => {
    const rows = historyQuery.data?.history ?? [];
    return [...rows]
      .reverse()
      .map((item) => ({
        time: formatTime(item.timestamp),
        score: item.score,
      }));
  }, [historyQuery.data]);

  const computeMutation = useMutation({
    mutationFn: async () => {
      setActionError(null);
      return computeRisk(vehicleId.trim(), {
        driver_state: parseJsonInput(driverStateJson, "driver_state"),
        road_state: parseJsonInput(roadStateJson, "road_state"),
        telemetry: parseJsonInput(telemetryJson, "telemetry"),
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
      return detectSafetyEvents(vehicleId.trim(), {
        driver_id: driverId.trim(),
        session_id: sessionId.trim() || undefined,
        driver_state: parseJsonInput(driverStateJson, "driver_state"),
        road_state: parseJsonInput(roadStateJson, "road_state"),
        telemetry: parseJsonInput(telemetryJson, "telemetry"),
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
      <section className="grid gap-4 rounded-2xl border border-slate-800 bg-slate-900/50 p-5 lg:grid-cols-3">
        <label className="block text-sm">
          <span className="mb-1 block text-slate-400">Vehicle ID</span>
          <input
            value={vehicleId}
            onChange={(e) => setVehicleId(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-400">Driver ID</span>
          <input
            value={driverId}
            onChange={(e) => setDriverId(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-400">Fleet org (WebSocket)</span>
          <input
            value={orgId}
            onChange={(e) => setOrgId(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
          />
        </label>
      </section>

      <div className="grid gap-6 xl:grid-cols-[320px_1fr]">
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Live composite risk</h2>
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                wsStatus === "connected"
                  ? "bg-emerald-500/15 text-emerald-300"
                  : wsStatus === "connecting"
                    ? "bg-amber-500/15 text-amber-300"
                    : "bg-slate-800 text-slate-400"
              }`}
            >
              WS {wsStatus}
            </span>
          </div>

          {displayedRisk ? (
            <div className="flex flex-col items-center gap-4">
              <RiskGauge
                score={Math.round(displayedRisk.score)}
                risk={displayedRisk.level}
              />
              <div className="w-full text-center">
                <p className="text-sm text-slate-400">
                  Updated {formatTime(displayedRisk.timestamp)}
                </p>
                {displayedRisk.message ? (
                  <p className="mt-1 text-xs text-amber-300">{displayedRisk.message}</p>
                ) : null}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">
              No risk score yet. Run compute or wait for a WebSocket update.
            </p>
          )}

          {wsError ? (
            <p className="mt-3 text-xs text-amber-300">{wsError}</p>
          ) : null}

          {displayedRisk?.reasons?.length ? (
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-semibold text-slate-300">Reasons</h3>
              <ul className="space-y-1 text-sm text-slate-400">
                {displayedRisk.reasons.map((reason) => (
                  <li key={reason}>• {reason}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {displayedRisk?.overrides?.length ? (
            <div className="mt-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-300">Overrides</h3>
              <ul className="space-y-1 text-sm text-rose-300">
                {displayedRisk.overrides.map((item) => (
                  <li key={item.rule_id}>{item.reason}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">Risk history</h2>
              <p className="text-sm text-slate-400">
                Persisted scores from Module 4F
              </p>
            </div>
            {historyQuery.data?.warning ? (
              <p className="text-xs text-amber-300">{historyQuery.data.warning}</p>
            ) : null}
          </div>

          {historyChartData.length > 0 ? (
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyChartData}>
                  <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                  <XAxis dataKey="time" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "#0f172a",
                      border: "1px solid #334155",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#f97316"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              No persisted history yet. Compute risk with persistence enabled.
            </p>
          )}
        </section>
      </div>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Demo inputs</h2>
            <p className="text-sm text-slate-400">
              JSON payloads sent to 4F compute and detect endpoints
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => computeMutation.mutate()}
              disabled={!vehicleValid || computeMutation.isPending}
              className="rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-500 disabled:opacity-50"
            >
              {computeMutation.isPending ? "Computing…" : "Compute risk"}
            </button>
            <button
              type="button"
              onClick={() => detectMutation.mutate()}
              disabled={!vehicleValid || !driverValid || detectMutation.isPending}
              className="rounded-lg bg-rose-700 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-600 disabled:opacity-50"
            >
              {detectMutation.isPending ? "Detecting…" : "Run event detection"}
            </button>
          </div>
        </div>

        <div className="mb-4 flex flex-wrap gap-2">
          {DEMO_SCENARIOS.map((scenario) => (
            <button
              key={scenario.id}
              type="button"
              onClick={() => applyScenario(scenario.id)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-semibold ${
                activeScenario === scenario.id
                  ? "border-orange-500/50 bg-orange-500/15 text-orange-200"
                  : "border-slate-700 text-slate-300 hover:bg-slate-800"
              }`}
              title={scenario.hint}
            >
              {scenario.label}
            </button>
          ))}
        </div>
        <p className="mb-4 text-xs text-slate-500">
          {
            DEMO_SCENARIOS.find((item) => item.id === activeScenario)
              ?.expectedEvents
          }
          {" · "}
          {
            DEMO_SCENARIOS.find((item) => item.id === activeScenario)?.hint
          }
        </p>

        <div className="grid gap-4 lg:grid-cols-3">
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">driver_state</span>
            <textarea
              value={driverStateJson}
              onChange={(e) => setDriverStateJson(e.target.value)}
              rows={10}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">road_state</span>
            <textarea
              value={roadStateJson}
              onChange={(e) => setRoadStateJson(e.target.value)}
              rows={10}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">telemetry</span>
            <textarea
              value={telemetryJson}
              onChange={(e) => setTelemetryJson(e.target.value)}
              rows={10}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs"
            />
          </label>
        </div>

        {actionError ? (
          <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {actionError}
          </p>
        ) : null}

        {detectMutation.data ? (
          <div className="mt-4 text-sm text-emerald-300">
            <p>
              Detection finished: {detectMutation.data.detected} detected,{" "}
              {detectMutation.data.persisted} persisted.
            </p>
            {detectMutation.data.events.length > 0 ? (
              <ul className="mt-2 list-inside list-disc text-slate-300">
                {detectMutation.data.events.map((event) => (
                  <li key={event.id}>
                    {event.event_type} ({event.severity})
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-amber-300">
                No events matched thresholds. Load the &quot;3 events&quot; or
                &quot;2 events&quot; scenario, or add confirmed road objects with
                closing speed (TTC) and/or consecutive_drowsy_frames &gt; 60.
              </p>
            )}
          </div>
        ) : null}
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Safety event feed</h2>
            <p className="text-sm text-slate-400">
              {events.length} events · {unacknowledged} unacknowledged
            </p>
          </div>
          <button
            type="button"
            onClick={() =>
              queryClient.invalidateQueries({ queryKey: ["safety-events", vehicleId] })
            }
            className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-semibold hover:bg-slate-800"
          >
            Refresh
          </button>
        </div>

        {eventsQuery.data?.warning ? (
          <p className="mb-4 text-sm text-amber-300">{eventsQuery.data.warning}</p>
        ) : null}

        {events.length === 0 ? (
          <p className="text-sm text-slate-500">
            No safety events stored for this vehicle yet. Run event detection with
            a seeded vehicle/driver in Postgres.
          </p>
        ) : (
          <div className="space-y-4">
            {events.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                driverId={driverId.trim()}
                onAcknowledged={() =>
                  queryClient.invalidateQueries({
                    queryKey: ["safety-events", vehicleId],
                  })
                }
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
