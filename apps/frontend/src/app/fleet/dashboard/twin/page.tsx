"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RoleShell } from "@/components/dashboard/RoleShell";
import { StatCard } from "@/components/dashboard/StatCard";
import { api } from "@/lib/api";

const DEMO_VEHICLE = "00000000-0000-4000-8000-000000000003";

export default function DigitalTwinPage() {
  const [vehicleId, setVehicleId] = useState(DEMO_VEHICLE);

  const twinQuery = useQuery({
    queryKey: ["digital-twin", vehicleId],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/industry/twin/${vehicleId}`);
      return data as {
        name?: string;
        model?: string;
        pose?: { x: number; y: number; heading_deg: number };
        telemetry?: {
          speed_kmh?: number;
          battery_soc_pct?: number;
          latitude?: number;
          longitude?: number;
        };
      };
    },
    refetchInterval: 3000,
  });

  const carbonQuery = useQuery({
    queryKey: ["carbon", vehicleId],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/industry/carbon/${vehicleId}`);
      return data as { efficiency_score?: number; kwh_per_100km_est?: number };
    },
  });

  const t = twinQuery.data;
  const pose = t?.pose;
  const telem = t?.telemetry;

  return (
    <RoleShell subtitle="Live 2D vehicle state twin (Spec Section 19.4)">
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Vehicle" value={t?.name || "—"} hint={t?.model} />
        <StatCard
          label="Speed"
          value={telem?.speed_kmh != null ? telem.speed_kmh.toFixed(0) : "—"}
          accent="sky"
        />
        <StatCard
          label="Battery"
          value={
            telem?.battery_soc_pct != null
              ? `${telem.battery_soc_pct.toFixed(0)}%`
              : "—"
          }
          accent="emerald"
        />
        <StatCard
          label="Efficiency"
          value={
            carbonQuery.data?.efficiency_score != null
              ? carbonQuery.data.efficiency_score.toFixed(0)
              : "—"
          }
          accent="amber"
          hint={
            carbonQuery.data?.kwh_per_100km_est
              ? `${carbonQuery.data.kwh_per_100km_est} kWh/100km`
              : undefined
          }
        />
      </div>

      <div className="relative h-80 overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            backgroundImage:
              "linear-gradient(#1e293b 1px, transparent 1px), linear-gradient(90deg, #1e293b 1px, transparent 1px)",
            backgroundSize: "32px 32px",
          }}
        />
        <div
          className="absolute left-1/2 top-1/2 h-16 w-10 -translate-x-1/2 -translate-y-1/2 rounded-md border-2 border-sky-400 bg-sky-500/40 shadow-[0_0_24px_rgba(56,189,248,0.35)] transition-transform duration-500"
          style={{
            transform: `translate(-50%, -50%) rotate(${pose?.heading_deg ?? 90}deg)`,
          }}
          aria-label="Vehicle twin pose"
        />
        <p className="absolute bottom-3 left-4 text-xs text-slate-500">
          lon {pose?.x?.toFixed?.(4) ?? "—"} · lat {pose?.y?.toFixed?.(4) ?? "—"} ·
          heading {pose?.heading_deg ?? "—"}°
        </p>
      </div>

      <label className="block max-w-md text-xs text-slate-500">
        Vehicle id
        <input
          value={vehicleId}
          onChange={(e) => setVehicleId(e.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
        />
      </label>
    </RoleShell>
  );
}
