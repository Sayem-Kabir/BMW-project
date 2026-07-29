"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getFleetIncidents, getFleetLeaderboard } from "@/lib/api";
import type { LeaderboardEntry } from "@/lib/types";

const ORG = "00000000-0000-4000-8000-000000000010";

function tierClass(tier: string) {
  if (tier === "green") return "bg-emerald-500/20 text-emerald-200 border-emerald-500/30";
  if (tier === "amber") return "bg-amber-500/20 text-amber-100 border-amber-500/30";
  return "bg-red-500/20 text-red-200 border-red-500/30";
}

function Sparkline({ values }: { values: number[] }) {
  if (!values.length) {
    return <span className="text-[10px] text-slate-500">—</span>;
  }
  const data = values.map((value, index) => ({ index, value }));
  return (
    <div className="h-8 w-28">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <Line
            type="monotone"
            dataKey="value"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function LeaderboardTable({ rows }: { rows: LeaderboardEntry[] }) {
  if (!rows.length) {
    return (
      <p className="text-sm text-slate-500">
        No leaderboard data yet. Run{" "}
        <code>python scripts/seed_safety_demo.py</code>.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="text-[11px] uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">Rank</th>
            <th className="px-3 py-2 font-medium">Driver</th>
            <th className="px-3 py-2 font-medium">Score</th>
            <th className="px-3 py-2 font-medium">Tier</th>
            <th className="px-3 py-2 font-medium">7d trend</th>
            <th className="px-3 py-2 font-medium">Events</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.driver_id}
              className="border-t border-slate-800/80 hover:bg-slate-900/80"
            >
              <td className="px-3 py-3 font-semibold text-slate-200">
                #{row.rank}
              </td>
              <td className="px-3 py-3">
                <p className="font-medium text-white">{row.name}</p>
                <p className="text-[11px] text-slate-500">{row.email || row.driver_id}</p>
              </td>
              <td className="px-3 py-3 text-lg font-semibold">
                {row.safety_score}
              </td>
              <td className="px-3 py-3">
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] uppercase ${tierClass(row.risk_tier)}`}
                >
                  {row.risk_tier}
                </span>
              </td>
              <td className="px-3 py-3">
                <Sparkline values={row.sparkline || []} />
              </td>
              <td className="px-3 py-3 text-slate-300">{row.event_count_7d}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function LeaderboardPanel() {
  const boardQuery = useQuery({
    queryKey: ["fleet-leaderboard", ORG],
    queryFn: () => getFleetLeaderboard(ORG, 7),
  });
  const incidentsQuery = useQuery({
    queryKey: ["fleet-incidents", ORG],
    queryFn: () => getFleetIncidents(ORG, 8),
  });

  const board = boardQuery.data?.leaderboard ?? [];
  const incidents = incidentsQuery.data?.incidents ?? [];
  const totalIncidents = incidents.reduce((sum, week) => sum + (week.total || 0), 0);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Metric
          label="Drivers ranked"
          value={boardQuery.isLoading ? "…" : board.length}
        />
        <Metric
          label="Top score"
          value={board[0] ? board[0].safety_score : "—"}
        />
        <Metric label="Incidents (8w)" value={totalIncidents} />
      </div>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="mb-3 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-slate-100">
            Driver leaderboard (7-day)
          </h2>
          <p className="text-[11px] text-slate-500">
            phase={boardQuery.data?.phase || "6D"}
          </p>
        </div>
        {boardQuery.isLoading ? (
          <p className="text-sm text-slate-500">Loading leaderboard…</p>
        ) : (
          <LeaderboardTable rows={board} />
        )}
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-100">
          Fleet incident trends (weekly)
        </h2>
        {incidentsQuery.isLoading ? (
          <p className="text-sm text-slate-500">Loading incidents…</p>
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={incidents}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="week_start" stroke="#94a3b8" fontSize={10} />
                  <YAxis allowDecimals={false} stroke="#94a3b8" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      background: "#0f172a",
                      border: "1px solid #334155",
                      borderRadius: 8,
                    }}
                  />
                  <Legend />
                  <Bar dataKey="CRITICAL" stackId="a" fill="#ef4444" />
                  <Bar dataKey="HIGH" stackId="a" fill="#f97316" />
                  <Bar dataKey="MEDIUM" stackId="a" fill="#eab308" />
                  <Bar dataKey="LOW" stackId="a" fill="#38bdf8" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={incidents}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="week_start" stroke="#94a3b8" fontSize={10} />
                  <YAxis allowDecimals={false} stroke="#94a3b8" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      background: "#0f172a",
                      border: "1px solid #334155",
                      borderRadius: 8,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="total"
                    stroke="#a78bfa"
                    strokeWidth={2}
                    name="Total incidents"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </section>
    </div>
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
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}
