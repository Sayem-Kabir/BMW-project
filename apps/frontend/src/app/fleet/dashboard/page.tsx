"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { AlertsCenter } from "@/components/fleet/AlertsCenter";
import { VehicleGrid } from "@/components/fleet/VehicleGrid";
import { RoleShell } from "@/components/dashboard/RoleShell";
import { StatCard } from "@/components/dashboard/StatCard";
import { useFleetWebSocket } from "@/hooks/useFleetWebSocket";

// Spec Phase 13 — code-split heavy map/chart bundles out of initial fleet shell
const FleetMap = dynamic(
  () => import("@/components/fleet/FleetMap").then((m) => m.FleetMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-64 items-center justify-center rounded-2xl border border-slate-800 text-sm text-slate-500">
        Loading map…
      </div>
    ),
  }
);
const RiskDistributionChart = dynamic(
  () =>
    import("@/components/fleet/RiskDistributionChart").then(
      (m) => m.RiskDistributionChart
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-56 items-center justify-center text-sm text-slate-500">
        Loading chart…
      </div>
    ),
  }
);

const ORG = "00000000-0000-4000-8000-000000000010";

export default function FleetDashboardPage() {
  const { connected, status, error, overview, vehicles, alerts, refresh } =
    useFleetWebSocket({ orgId: ORG });

  const severityCounts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  for (const alert of alerts) {
    const key = String(alert.severity || "").toUpperCase();
    if (key in severityCounts) {
      severityCounts[key as keyof typeof severityCounts] += 1;
    }
  }
  const alertTotal =
    overview?.active_alerts ??
    vehicles.reduce((sum, v) => sum + (v.active_alerts || 0), 0);

  return (
    <RoleShell subtitle="Org-scoped live vehicles, risk distribution, and alerts">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-400">
          Live WebSocket:{" "}
          <span className={connected ? "text-emerald-300" : "text-amber-300"}>
            {status}
          </span>
          {error ? <span className="ml-2 text-red-300">{error}</span> : null}
        </p>
        <div className="flex gap-2">
          <Link
            href="/fleet/dashboard/analytics"
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800"
          >
            Leaderboard
          </Link>
          <button
            type="button"
            onClick={() => void refresh()}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Vehicles" value={overview?.vehicle_count ?? "—"} />
        <StatCard
          label="Online"
          value={overview?.online_vehicles ?? "—"}
          accent="emerald"
        />
        <StatCard
          label="Active alerts"
          value={alertTotal}
          accent="amber"
          hint={`CRIT ${severityCounts.CRITICAL} · HIGH ${severityCounts.HIGH}`}
        />
        <StatCard
          label="Avg risk"
          value={overview ? overview.average_risk.toFixed(1) : "—"}
          accent="rose"
        />
      </div>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-200">Vehicle status</h2>
          <VehicleGrid vehicles={vehicles} />
        </div>
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-200">Map + risk</h2>
          <FleetMap vehicles={vehicles} />
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <RiskDistributionChart distribution={overview?.risk_distribution} />
          </div>
        </div>
      </section>

      <AlertsCenter compact />
    </RoleShell>
  );
}
