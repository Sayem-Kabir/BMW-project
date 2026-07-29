"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RoleShell } from "@/components/dashboard/RoleShell";
import { StatCard } from "@/components/dashboard/StatCard";
import { TelemetryChart } from "@/components/dashboard/TelemetryChart";
import { EventList } from "@/components/dashboard/EventList";
import { getMe, getFleetAlerts, api } from "@/lib/api";

const DEMO_VEHICLE = "00000000-0000-4000-8000-000000000003";

export default function DriverDashboardPage() {
  const [driverId, setDriverId] = useState<string | null>(null);
  const [vehicleId, setVehicleId] = useState(DEMO_VEHICLE);

  useEffect(() => {
    getMe()
      .then((me) => {
        if (me.driver_id) setDriverId(me.driver_id);
      })
      .catch(() => undefined);
  }, []);

  const scoreQuery = useQuery({
    queryKey: ["driver-weekly", driverId],
    enabled: Boolean(driverId),
    queryFn: async () => {
      const { data } = await api.get(
        `/api/v1/analytics/driver/${driverId}/weekly`
      );
      return data as {
        safety_score?: number;
        sparkline?: Array<number | { day: string; score: number }>;
      };
    },
  });

  const telemetryQuery = useQuery({
    queryKey: ["driver-telemetry", vehicleId],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/telemetry/${vehicleId}`);
      return data as {
        points: Array<{
          time: string;
          speed_kmh?: number | null;
          battery_soc_pct?: number | null;
        }>;
      };
    },
    refetchInterval: 5000,
  });

  const alertsQuery = useQuery({
    queryKey: ["driver-alerts"],
    queryFn: () => getFleetAlerts(undefined, 20),
  });

  const score = scoreQuery.data?.safety_score;
  const sparkRaw = scoreQuery.data?.sparkline || [];
  const spark = sparkRaw.map((p, i) =>
    typeof p === "number"
      ? { day: `d${i + 1}`, score: p }
      : { day: p.day, score: p.score }
  );
  const events = (alertsQuery.data?.alerts || []).map((a) => ({
    id: a.id,
    event_type: a.event_type,
    severity: a.severity,
    timestamp: a.timestamp,
    vehicle_id: a.vehicle_id,
  }));

  return (
    <RoleShell subtitle="Your safety score, live telemetry, and personal event history">
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="Safety score"
          value={score != null ? Number(score).toFixed(0) : "—"}
          accent="emerald"
          hint={driverId ? `driver ${driverId.slice(0, 8)}…` : "Link a driver profile"}
        />
        <StatCard
          label="Open alerts"
          value={events.length}
          accent="amber"
        />
        <StatCard
          label="Vehicle"
          value={vehicleId.slice(0, 8) + "…"}
          accent="sky"
          hint="Demo i4 feed"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <TelemetryChart
          points={telemetryQuery.data?.points || []}
          metric="speed_kmh"
          label="Live speed"
        />
        <TelemetryChart
          points={telemetryQuery.data?.points || []}
          metric="battery_soc_pct"
          label="Battery SoC %"
        />
      </div>

      {spark.length || driverId ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Weekly score trend
            </p>
            {driverId ? (
              <button
                type="button"
                className="text-xs text-emerald-300 hover:text-emerald-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-300"
                onClick={async () => {
                  const { data } = await api.get(
                    `/api/v1/analytics/driver/${driverId}/weekly.pdf`,
                    { responseType: "blob" }
                  );
                  const url = URL.createObjectURL(data as Blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `driver-weekly.pdf`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                Download PDF report
              </button>
            ) : null}
          </div>
          {spark.length ? (
            <div className="flex h-16 items-end gap-1">
              {spark.map((p) => (
                <div
                  key={p.day}
                  className="flex-1 rounded-t bg-emerald-500/70"
                  style={{ height: `${Math.max(8, Number(p.score) || 0)}%` }}
                  title={`${p.day}: ${p.score}`}
                />
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No sparkline data yet</p>
          )}
        </div>
      ) : null}

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200">My events</h2>
          <Link
            href="/assistant"
            className="text-xs text-emerald-300 hover:text-emerald-200"
          >
            Ask the assistant →
          </Link>
        </div>
        <EventList events={events} emptyLabel="No open alerts for your scope" />
      </div>

      <label className="block max-w-md text-xs text-slate-500">
        Telemetry vehicle id
        <input
          value={vehicleId}
          onChange={(e) => setVehicleId(e.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
        />
      </label>
    </RoleShell>
  );
}
