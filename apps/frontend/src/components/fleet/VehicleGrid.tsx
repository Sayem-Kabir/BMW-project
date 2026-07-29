"use client";

import Link from "next/link";
import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type UIEvent,
} from "react";
import type { FleetVehicleCard } from "@/lib/types";

function statusClass(status: string) {
  if (status === "critical") return "border-red-500/40 bg-red-500/10 text-red-200";
  if (status === "maintenance")
    return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
}

const ROW_HEIGHT = 132;
const OVERSCAN = 4;

const VehicleCard = memo(function VehicleCard({
  vehicle,
}: {
  vehicle: FleetVehicleCard;
}) {
  return (
    <Link
      href={`/fleet/dashboard/vehicles/${vehicle.id}`}
      className={`block rounded-xl border p-4 transition hover:border-sky-500/50 ${statusClass(vehicle.status)}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-white">{vehicle.name}</p>
          <p className="text-xs text-slate-400">
            {vehicle.model || "BMW"} · {vehicle.year || "—"}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] uppercase tracking-wide">
            {vehicle.status}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
              vehicle.risk_level === "CRITICAL" || vehicle.risk_level === "HIGH"
                ? "bg-red-500/20 text-red-200"
                : vehicle.risk_level === "MEDIUM"
                  ? "bg-amber-500/20 text-amber-100"
                  : "bg-emerald-500/20 text-emerald-200"
            }`}
          >
            {vehicle.risk_level}
          </span>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
        <div>
          <p className="text-slate-400">Risk</p>
          <p className="font-semibold">{Number(vehicle.risk_score || 0).toFixed(0)}</p>
        </div>
        <div>
          <p className="text-slate-400">Alerts</p>
          <p className="font-semibold">{vehicle.active_alerts}</p>
        </div>
        <div>
          <p className="text-slate-400">Health</p>
          <p className="font-semibold">
            {vehicle.worst_health != null
              ? `${(vehicle.worst_health * 100).toFixed(0)}%`
              : "—"}
          </p>
        </div>
      </div>
    </Link>
  );
});

/** Spec Phase 13 — virtualized vehicle list for 100+ fleet. */
export function VehicleGrid({ vehicles }: { vehicles: FleetVehicleCard[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewport, setViewport] = useState(480);

  useEffect(() => {
    const el = parentRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setViewport(el.clientHeight || 480));
    ro.observe(el);
    setViewport(el.clientHeight || 480);
    return () => ro.disconnect();
  }, []);

  const onScroll = useCallback((e: UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  const { start, end, offsetY, totalHeight } = useMemo(() => {
    const visible = Math.ceil(viewport / ROW_HEIGHT) + OVERSCAN * 2;
    const startIdx = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    const endIdx = Math.min(vehicles.length, startIdx + visible);
    return {
      start: startIdx,
      end: endIdx,
      offsetY: startIdx * ROW_HEIGHT,
      totalHeight: vehicles.length * ROW_HEIGHT,
    };
  }, [scrollTop, viewport, vehicles.length]);

  if (!vehicles.length) {
    return (
      <p className="text-sm text-slate-500">
        No vehicles yet. Run <code>python scripts/seed_safety_demo.py</code>.
      </p>
    );
  }

  // Small fleets: keep the responsive grid; large fleets: virtualize
  if (vehicles.length < 24) {
    return (
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {vehicles.map((vehicle) => (
          <VehicleCard key={vehicle.id} vehicle={vehicle} />
        ))}
      </div>
    );
  }

  const slice = vehicles.slice(start, end);

  return (
    <div
      ref={parentRef}
      onScroll={onScroll}
      className="max-h-[36rem] overflow-y-auto rounded-xl border border-slate-800"
      role="list"
      aria-label="Fleet vehicles"
    >
      <div style={{ height: totalHeight, position: "relative" }}>
        <div
          style={{ transform: `translateY(${offsetY}px)` }}
          className="grid gap-3 p-2 md:grid-cols-2 xl:grid-cols-3"
        >
          {slice.map((vehicle) => (
            <div key={vehicle.id} role="listitem" style={{ minHeight: ROW_HEIGHT - 12 }}>
              <VehicleCard vehicle={vehicle} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
