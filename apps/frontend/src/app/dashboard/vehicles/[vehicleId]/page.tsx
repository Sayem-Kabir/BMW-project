"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { XaiPanel } from "@/components/fleet/XaiPanel";
import {
  getCurrentRisk,
  getFleetVehicles,
  getMaintenanceLatest,
  getSafetyEvents,
  getTelemetryHistory,
} from "@/lib/api";
import type { FleetVehicleCard, MaintenancePrediction } from "@/lib/types";

const ORG = "00000000-0000-4000-8000-000000000010";

function healthTone(score: number | null | undefined) {
  if (score == null) return "border-slate-800 text-slate-300";
  if (score <= 0.35) return "border-red-500/40 bg-red-500/10 text-red-100";
  if (score <= 0.6) return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
}

function severityFromShap(row: MaintenancePrediction): string {
  const shap = row.shap_explanation as { severity?: string } | null | undefined;
  return String(shap?.severity || "unknown");
}

export default function VehicleDetailPage() {
  const params = useParams<{ vehicleId: string }>();
  const vehicleId = params.vehicleId;
  const [selectedComponent, setSelectedComponent] = useState<string | null>(
    null
  );
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  const vehicleQuery = useQuery({
    queryKey: ["fleet-vehicles", ORG],
    queryFn: () => getFleetVehicles(ORG),
    enabled: Boolean(vehicleId),
  });
  const telemetryQuery = useQuery({
    queryKey: ["telemetry", vehicleId],
    queryFn: () => getTelemetryHistory(vehicleId),
    enabled: Boolean(vehicleId),
  });
  const eventsQuery = useQuery({
    queryKey: ["vehicle-events", vehicleId],
    queryFn: () => getSafetyEvents(vehicleId, { limit: 20 }),
    enabled: Boolean(vehicleId),
    refetchInterval: 15000,
  });
  const maintenanceQuery = useQuery({
    queryKey: ["vehicle-maintenance", vehicleId],
    queryFn: () => getMaintenanceLatest(vehicleId),
    enabled: Boolean(vehicleId),
  });
  const riskQuery = useQuery({
    queryKey: ["vehicle-risk", vehicleId],
    queryFn: () => getCurrentRisk(vehicleId),
    enabled: Boolean(vehicleId),
    refetchInterval: 10000,
  });

  const vehicle: FleetVehicleCard | undefined = (
    vehicleQuery.data?.vehicles || []
  ).find((item) => item.id === vehicleId);

  const points = telemetryQuery.data?.points ?? [];
  const events = eventsQuery.data?.events ?? [];
  const componentRows = maintenanceQuery.data?.predictions ?? [];
  const riskScore = riskQuery.data?.score ?? vehicle?.risk_score;
  const riskLevel = riskQuery.data?.level ?? vehicle?.risk_level ?? "—";

  const activeComponent = useMemo(() => {
    if (selectedComponent) return selectedComponent;
    return componentRows[0]?.component ?? null;
  }, [selectedComponent, componentRows]);

  const activeEventId = useMemo(() => {
    if (selectedEventId) return selectedEventId;
    return events[0]?.id ?? null;
  }, [selectedEventId, events]);

  const activeEventType =
    events.find((event) => event.id === activeEventId)?.event_type ?? undefined;

  const assistantHref = `/assistant?vehicle_id=${encodeURIComponent(vehicleId || "")}`;

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 bg-slate-900/50">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-sky-300">
              Phase 6 · Module 6C
            </p>
            <h1 className="text-2xl font-bold">
              {vehicle?.name || "Vehicle detail"}
            </h1>
            <p className="text-sm text-slate-400">
              {vehicle?.model || "BMW"} · {vehicle?.year || "—"} ·{" "}
              <span className="font-mono text-xs text-slate-500">{vehicleId}</span>
            </p>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/dashboard" className="text-slate-400 hover:text-white">
              Dashboard
            </Link>
            <Link
              href={assistantHref}
              className="rounded-lg bg-sky-700 px-3 py-1.5 text-white hover:bg-sky-600"
            >
              Ask assistant
            </Link>
            <Link
              href="/dashboard/xai"
              className="text-slate-400 hover:text-white"
            >
              Grad-CAM
            </Link>
            <Link href="/safety" className="text-slate-400 hover:text-white">
              Safety
            </Link>
            <Link
              href="/maintenance"
              className="text-slate-400 hover:text-white"
            >
              Maintenance
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">
        <div className="grid gap-4 md:grid-cols-4">
          <Stat
            label="Risk"
            value={`${Number(riskScore ?? 0).toFixed(0)} · ${riskLevel}`}
          />
          <Stat label="Status" value={vehicle?.status || "—"} />
          <Stat label="Active alerts" value={vehicle?.active_alerts ?? events.length} />
          <Stat
            label="Telemetry"
            value={telemetryQuery.data?.source || "—"}
          />
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
          <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <h2 className="mb-3 text-sm font-semibold">
              Telemetry time-series
            </h2>
            <div className="h-80">
              {telemetryQuery.isLoading ? (
                <p className="text-sm text-slate-500">Loading telemetry…</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={points}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="time" hide />
                    <YAxis stroke="#94a3b8" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        background: "#0f172a",
                        border: "1px solid #334155",
                        borderRadius: 8,
                      }}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="speed_kmh"
                      stroke="#38bdf8"
                      dot={false}
                      name="Speed km/h"
                    />
                    <Line
                      type="monotone"
                      dataKey="battery_soc_pct"
                      stroke="#a78bfa"
                      dot={false}
                      name="Battery %"
                    />
                    <Line
                      type="monotone"
                      dataKey="tire_rl"
                      stroke="#f97316"
                      dot={false}
                      name="Tire RL PSI"
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
            <p className="mt-2 text-xs text-slate-500">
              {points.length} points · source={telemetryQuery.data?.source || "—"}
            </p>
          </section>

          <div className="space-y-6">
            <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <h2 className="mb-3 text-sm font-semibold">
                Maintenance component health
              </h2>
              <div className="space-y-2">
                {componentRows.length ? (
                  componentRows.map((row) => {
                    const selected = row.component === activeComponent;
                    return (
                      <button
                        type="button"
                        key={row.component || row.id}
                        onClick={() =>
                          setSelectedComponent(row.component || null)
                        }
                        className={`w-full rounded-xl border px-3 py-3 text-left transition ${healthTone(row.health_score)} ${
                          selected ? "ring-2 ring-violet-400/60" : ""
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2 text-sm">
                          <span className="font-medium capitalize">
                            {row.component}
                          </span>
                          <span className="font-semibold">
                            {(Number(row.health_score) * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="mt-1 text-[11px] opacity-80">
                          severity={severityFromShap(row)}
                          {row.confidence != null
                            ? ` · confidence=${Number(row.confidence).toFixed(2)}`
                            : ""}
                        </p>
                      </button>
                    );
                  })
                ) : (
                  <p className="text-sm text-slate-500">
                    No maintenance predictions for this vehicle yet.
                  </p>
                )}
              </div>
              {vehicleId && activeComponent ? (
                <XaiPanel
                  vehicleId={vehicleId}
                  component={activeComponent}
                  className="mt-3"
                  autoLabel="Explain SHAP"
                />
              ) : null}
            </section>

            <section className="rounded-2xl border border-sky-700/40 bg-sky-950/30 p-4">
              <h2 className="mb-2 text-sm font-semibold text-sky-100">
                AI vehicle assistant
              </h2>
              <p className="mb-3 text-xs text-slate-400">
                Open a grounded chat scoped to this vehicle for TPMS, OBD, and
                service questions.
              </p>
              <Link
                href={assistantHref}
                className="inline-flex rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500"
              >
                Chat about this vehicle
              </Link>
            </section>
          </div>
        </div>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="mb-3 text-sm font-semibold">
            Current session events timeline
          </h2>
          <div className="max-h-96 space-y-2 overflow-y-auto">
            {eventsQuery.isLoading ? (
              <p className="text-sm text-slate-500">Loading events…</p>
            ) : null}
            {events.map((event) => {
              const selected = event.id === activeEventId;
              return (
                <button
                  type="button"
                  key={event.id}
                  onClick={() => setSelectedEventId(event.id)}
                  className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                    selected
                      ? "border-violet-500/50 bg-violet-950/30"
                      : "border-slate-800 bg-slate-950/60 hover:border-slate-700"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium text-slate-100">
                      {event.event_type}
                    </p>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] uppercase ${
                        event.severity === "CRITICAL" ||
                        event.severity === "HIGH"
                          ? "bg-red-500/20 text-red-200"
                          : event.severity === "MEDIUM"
                            ? "bg-amber-500/20 text-amber-100"
                            : "bg-slate-700 text-slate-200"
                      }`}
                    >
                      {event.severity}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{event.timestamp}</p>
                  {event.xai_explanation ? (
                    <p className="mt-2 text-xs leading-relaxed text-slate-300">
                      {event.xai_explanation}
                    </p>
                  ) : null}
                </button>
              );
            })}
            {!eventsQuery.isLoading && !events.length ? (
              <p className="text-sm text-slate-500">
                No safety events for this vehicle.
              </p>
            ) : null}
          </div>
          {activeEventId ? (
            <XaiPanel
              eventId={activeEventId}
              eventType={activeEventType}
              className="mt-3"
              autoLabel="Explain event"
            />
          ) : null}
        </section>
      </div>
    </main>
  );
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 text-lg font-semibold capitalize">{value}</p>
    </div>
  );
}
