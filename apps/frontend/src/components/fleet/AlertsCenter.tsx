"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  acknowledgeFleetAlert,
  clipLink,
  getFleetAlerts,
  getFleetVehicles,
} from "@/lib/api";
import type { FleetAlert } from "@/lib/types";
import { XaiPanel } from "@/components/fleet/XaiPanel";

const ORG = "00000000-0000-4000-8000-000000000010";

type SeverityFilter = "ALL" | "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

function severityTone(severity: string) {
  const key = severity.toUpperCase();
  if (key === "CRITICAL") return "border-red-500/40 bg-red-500/10 text-red-100";
  if (key === "HIGH") return "border-orange-500/40 bg-orange-500/10 text-orange-100";
  if (key === "MEDIUM") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-sky-500/40 bg-sky-500/10 text-sky-100";
}

export function AlertsCenter({ compact = false }: { compact?: boolean }) {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<SeverityFilter>("ALL");
  const [expandedXai, setExpandedXai] = useState<string | null>(null);
  const [ackMessage, setAckMessage] = useState<string | null>(null);

  const alertsQuery = useQuery({
    queryKey: ["fleet-alerts", ORG],
    queryFn: () => getFleetAlerts(ORG, compact ? 8 : 50),
    refetchInterval: 15000,
  });
  const vehiclesQuery = useQuery({
    queryKey: ["fleet-vehicles", ORG],
    queryFn: () => getFleetVehicles(ORG),
  });

  const vehicleNames = useMemo(() => {
    const map: Record<string, string> = {};
    for (const vehicle of vehiclesQuery.data?.vehicles || []) {
      map[vehicle.id] = vehicle.name;
    }
    return map;
  }, [vehiclesQuery.data?.vehicles]);

  const ack = useMutation({
    mutationFn: (id: string) => acknowledgeFleetAlert(id),
    onSuccess: (_data, id) => {
      setAckMessage(`Acknowledged alert ${id.slice(0, 8)}…`);
      queryClient.invalidateQueries({ queryKey: ["fleet-alerts", ORG] });
      queryClient.invalidateQueries({ queryKey: ["fleet-vehicles", ORG] });
    },
    onError: (err) => {
      setAckMessage(err instanceof Error ? err.message : "Acknowledge failed");
    },
  });

  const alerts = alertsQuery.data?.alerts ?? [];
  const filtered = alerts.filter((alert) =>
    filter === "ALL" ? true : alert.severity.toUpperCase() === filter
  );

  const counts = {
    ALL: alerts.length,
    CRITICAL: 0,
    HIGH: 0,
    MEDIUM: 0,
    LOW: 0,
  };
  for (const alert of alerts) {
    const key = alert.severity.toUpperCase() as keyof typeof counts;
    if (key in counts) counts[key] += 1;
  }

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-100">
            {compact ? "Active alerts" : "Unacknowledged alert inbox"}
          </h2>
          <p className="text-xs text-slate-500">
            Sorted by severity · {alerts.length} open
          </p>
        </div>
        {compact ? (
          <Link
            href="/fleet/dashboard/alerts"
            className="text-xs text-sky-300 hover:text-sky-200"
          >
            Open alerts center
          </Link>
        ) : null}
      </div>

      {!compact ? (
        <div className="mb-4 flex flex-wrap gap-2">
          {(
            ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"] as SeverityFilter[]
          ).map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setFilter(key)}
              className={`rounded-full border px-3 py-1 text-[11px] uppercase tracking-wide ${
                filter === key
                  ? "border-sky-500/50 bg-sky-500/15 text-sky-100"
                  : "border-slate-700 text-slate-400 hover:bg-slate-800"
              }`}
            >
              {key} {counts[key]}
            </button>
          ))}
        </div>
      ) : null}

      {ackMessage ? (
        <p className="mb-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200">
          {ackMessage}
        </p>
      ) : null}

      {alertsQuery.isLoading ? (
        <p className="text-sm text-slate-500">Loading alerts…</p>
      ) : null}

      {!alertsQuery.isLoading && filtered.length === 0 ? (
        <p className="text-sm text-slate-500">No unacknowledged alerts.</p>
      ) : (
        <div className="space-y-3">
          {filtered.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              vehicleName={vehicleNames[alert.vehicle_id]}
              compact={compact}
              pending={ack.isPending}
              showXai={expandedXai === alert.id}
              onToggleXai={() =>
                setExpandedXai((prev) => (prev === alert.id ? null : alert.id))
              }
              onAcknowledge={() => ack.mutate(alert.id)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function AlertCard({
  alert,
  vehicleName,
  compact,
  pending,
  showXai,
  onToggleXai,
  onAcknowledge,
}: {
  alert: FleetAlert;
  vehicleName?: string;
  compact: boolean;
  pending: boolean;
  showXai: boolean;
  onToggleXai: () => void;
  onAcknowledge: () => void;
}) {
  const clip = clipLink(alert.video_clip_url);

  return (
    <div
      className={`rounded-xl border bg-slate-950/70 p-4 ${severityTone(alert.severity)}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-white">
              {alert.event_type.replace(/_/g, " ")}
            </p>
            <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] uppercase">
              {alert.severity}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            {vehicleName || `Vehicle ${alert.vehicle_id.slice(0, 8)}…`} ·{" "}
            {alert.timestamp || "—"}
          </p>
        </div>
        <button
          type="button"
          disabled={pending}
          onClick={onAcknowledge}
          className="rounded-lg border border-slate-600 bg-slate-900/70 px-3 py-1.5 text-xs font-medium text-slate-100 hover:bg-slate-800 disabled:opacity-50"
        >
          Acknowledge
        </button>
      </div>

      {alert.xai_explanation ? (
        <p className="mt-3 whitespace-pre-wrap text-xs leading-relaxed text-slate-200">
          {alert.xai_explanation}
        </p>
      ) : (
        <p className="mt-3 text-xs text-slate-500">No XAI explanation stored.</p>
      )}

      <div className="mt-3 flex flex-wrap gap-3 text-xs">
        {clip.href ? (
          <a
            href={clip.href}
            target="_blank"
            rel="noreferrer"
            className="text-sky-300 hover:text-sky-200"
          >
            Open clip
          </a>
        ) : (
          <span className="text-slate-500">No clip stored</span>
        )}
        <Link
          href={`/fleet/dashboard/vehicles/${alert.vehicle_id}`}
          className="text-slate-300 hover:text-white"
        >
          Vehicle detail
        </Link>
        {!compact ? (
          <button
            type="button"
            onClick={onToggleXai}
            className="text-violet-300 hover:text-violet-200"
          >
            {showXai ? "Hide XAI panel" : "XAI preview"}
          </button>
        ) : null}
      </div>

      {!compact && showXai ? (
        <XaiPanel eventId={alert.id} className="mt-3" />
      ) : null}
    </div>
  );
}
