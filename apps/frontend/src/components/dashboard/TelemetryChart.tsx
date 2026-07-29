"use client";

import { memo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type TelemetryPoint = {
  time: string;
  speed_kmh?: number | null;
  battery_soc_pct?: number | null;
};

function TelemetryChartInner({
  points,
  metric = "speed_kmh",
  label = "Speed (km/h)",
}: {
  points: TelemetryPoint[];
  metric?: "speed_kmh" | "battery_soc_pct";
  label?: string;
}) {
  const data = points.map((p, i) => ({
    i,
    label: p.time.slice(11, 16) || String(i),
    value: Number(p[metric] ?? 0),
  }));

  if (!data.length) {
    return (
      <div className="flex h-48 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900/60 text-sm text-slate-500">
        No telemetry yet
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <div className="h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
            <XAxis dataKey="label" stroke="#64748b" tick={{ fontSize: 10 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} width={36} />
            <Tooltip
              contentStyle={{
                background: "#0f172a",
                border: "1px solid #334155",
                borderRadius: 8,
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#38bdf8"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/** Spec Phase 13 — memoized so WS ticks don't re-render sibling charts. */
export const TelemetryChart = memo(TelemetryChartInner);
