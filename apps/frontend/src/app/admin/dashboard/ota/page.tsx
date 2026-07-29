"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RoleShell } from "@/components/dashboard/RoleShell";
import { StatCard } from "@/components/dashboard/StatCard";
import { api } from "@/lib/api";

export default function OtaCanaryPage() {
  const qc = useQueryClient();
  const [percent, setPercent] = useState(10);
  const [message, setMessage] = useState<string | null>(null);

  const statusQuery = useQuery({
    queryKey: ["ota-canary"],
    queryFn: async () => {
      const { data } = await api.get("/api/v1/industry/ota/canary");
      return data as {
        active?: boolean;
        model_name?: string;
        version?: string;
        fleet_percent?: number;
        error_rate?: number;
      };
    },
    refetchInterval: 5000,
  });

  const startMut = useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/api/v1/industry/ota/canary", {
        model_name: "driver_monitor",
        version: "canary",
        fleet_percent: percent,
      });
      return data;
    },
    onSuccess: () => {
      setMessage("Canary started");
      void qc.invalidateQueries({ queryKey: ["ota-canary"] });
    },
    onError: () => setMessage("Failed to start canary (admin role required)"),
  });

  const rollbackMut = useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/api/v1/industry/ota/canary/rollback");
      return data;
    },
    onSuccess: () => {
      setMessage("Rolled back");
      void qc.invalidateQueries({ queryKey: ["ota-canary"] });
    },
  });

  const s = statusQuery.data;

  return (
    <RoleShell subtitle="OTA model canary rollout (Spec Section 19.2)">
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          label="Canary"
          value={s?.active ? "ACTIVE" : "idle"}
          accent={s?.active ? "amber" : "emerald"}
        />
        <StatCard label="Model" value={s?.model_name || "—"} />
        <StatCard
          label="Fleet %"
          value={s?.fleet_percent != null ? `${s.fleet_percent}%` : "—"}
        />
        <StatCard
          label="Error rate"
          value={s?.error_rate != null ? `${s.error_rate}%` : "0%"}
          accent="rose"
        />
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs text-slate-400">
          Fleet percent
          <input
            type="number"
            min={1}
            max={100}
            value={percent}
            onChange={(e) => setPercent(Number(e.target.value))}
            className="mt-1 block w-28 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          />
        </label>
        <button
          type="button"
          className="primary-button"
          onClick={() => startMut.mutate()}
        >
          Start canary
        </button>
        <button
          type="button"
          className="danger-button"
          onClick={() => rollbackMut.mutate()}
        >
          Rollback
        </button>
      </div>
      {message ? <p className="text-sm text-slate-400">{message}</p> : null}
    </RoleShell>
  );
}
