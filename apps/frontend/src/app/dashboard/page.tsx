"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { AuthStatus } from "@/components/AuthStatus";
import { useFleetWebSocket } from "@/hooks/useFleetWebSocket";

const FleetMap = dynamic(
  () => import("@/components/fleet/FleetMap").then((m) => m.FleetMap),
  { ssr: false, loading: () => <div className="h-64 animate-pulse rounded-xl bg-slate-800" /> }
);
const VehicleGrid = dynamic(
  () => import("@/components/fleet/VehicleGrid").then((m) => m.VehicleGrid),
  { loading: () => <div className="h-48 animate-pulse rounded-xl bg-slate-800" /> }
);
const RiskDistributionChart = dynamic(
  () => import("@/components/fleet/RiskDistributionChart").then((m) => m.RiskDistributionChart),
  { loading: () => <div className="h-32 animate-pulse rounded-xl bg-slate-800" /> }
);
const AlertsCenter = dynamic(
  () => import("@/components/fleet/AlertsCenter").then((m) => m.AlertsCenter),
  { loading: () => <div className="h-40 animate-pulse rounded-xl bg-slate-800" /> }
);

const ORG = "00000000-0000-4000-8000-000000000010";

export default function DashboardPage() {
  const { connected, status, error, overview, vehicles, alerts, refresh } =
    useFleetWebSocket({ orgId: ORG });

  const severityCounts = {
    CRITICAL: 0,
    HIGH: 0,
    MEDIUM: 0,
    LOW: 0,
  };
  for (const alert of alerts) {
    const key = String(alert.severity || "").toUpperCase();
    if (key in severityCounts) {
      severityCounts[key as keyof typeof severityCounts] += 1;
    }
  }
  // Fallback from vehicle active_alerts when WS alert buffer is empty.
  const alertTotal =
    overview?.active_alerts ??
    vehicles.reduce((sum, v) => sum + (v.active_alerts || 0), 0);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 bg-slate-900/50">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-sky-300">
              Phase 6 · Module 6B
            </p>
            <h1 className="text-2xl font-bold">Fleet Overview</h1>
            <p className="text-sm text-slate-400">
              Live multi-vehicle status, risk distribution, and demo map
            </p>
          </div>
          <nav className="flex flex-wrap gap-3 text-sm">
            <Link href="/" className="text-slate-400 hover:text-white">
              Home
            </Link>
            <Link
              href="/dashboard/analytics"
              className="text-slate-400 hover:text-white"
            >
              Analytics
            </Link>
            <Link
              href="/dashboard/alerts"
              className="text-slate-400 hover:text-white"
            >
              Alerts
            </Link>
            <Link
              href="/dashboard/xai"
              className="text-slate-400 hover:text-white"
            >
              Grad-CAM
            </Link>
            <Link href="/demo" className="text-slate-400 hover:text-white">
              Demo
            </Link>
            <AuthStatus />
            <Link href="/safety" className="text-slate-400 hover:text-white">
              Safety
            </Link>
            <Link href="/assistant" className="text-slate-400 hover:text-white">
              Assistant
            </Link>
            <Link
              href="/maintenance"
              className="text-slate-400 hover:text-white"
            >
              Maintenance
            </Link>
          </nav>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-slate-400">
            Live WebSocket:{" "}
            <span className={connected ? "text-emerald-300" : "text-amber-300"}>
              {status}
            </span>
            {error ? <span className="ml-2 text-red-300">{error}</span> : null}
          </p>
          <button
            type="button"
            onClick={() => void refresh()}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800"
          >
            Refresh
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Vehicles" value={overview?.vehicle_count ?? "—"} />
          <Metric label="Online" value={overview?.online_vehicles ?? "—"} />
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <p className="text-sm text-slate-400">Active alerts</p>
            <p className="mt-1 text-2xl font-semibold">{alertTotal}</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              <SeverityBadge label="CRIT" count={severityCounts.CRITICAL} tone="red" />
              <SeverityBadge label="HIGH" count={severityCounts.HIGH} tone="orange" />
              <SeverityBadge label="MED" count={severityCounts.MEDIUM} tone="amber" />
              <SeverityBadge label="LOW" count={severityCounts.LOW} tone="sky" />
            </div>
          </div>
          <Metric
            label="Avg risk"
            value={overview ? overview.average_risk.toFixed(1) : "—"}
          />
        </div>

        <section className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold text-slate-200">
                Vehicle status grid
              </h2>
              <div className="flex gap-2 text-[10px] uppercase tracking-wide text-slate-500">
                <span className="text-emerald-300">Operational</span>
                <span className="text-amber-300">Maintenance</span>
                <span className="text-red-300">Critical</span>
              </div>
            </div>
            <VehicleGrid vehicles={vehicles} />
          </div>
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-slate-200">
              Live map (demo GPS)
            </h2>
            <FleetMap vehicles={vehicles} />
            <h2 className="text-sm font-semibold text-slate-200">
              Fleet risk distribution
            </h2>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <RiskDistributionChart
                distribution={overview?.risk_distribution}
              />
            </div>
          </div>
        </section>

        <AlertsCenter compact />
      </div>
    </main>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function SeverityBadge({
  label,
  count,
  tone,
}: {
  label: string;
  count: number;
  tone: "red" | "orange" | "amber" | "sky";
}) {
  const tones = {
    red: "border-red-500/40 bg-red-500/10 text-red-200",
    orange: "border-orange-500/40 bg-orange-500/10 text-orange-200",
    amber: "border-amber-500/40 bg-amber-500/10 text-amber-100",
    sky: "border-sky-500/40 bg-sky-500/10 text-sky-200",
  };
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${tones[tone]}`}
    >
      {label} {count}
    </span>
  );
}
