"use client";

import { useRef, useState } from "react";
import { analyzeCabinFrame } from "@/lib/api";
import type { CabinOccupancy } from "@/lib/types";

const SEAT_LABELS: Record<string, string> = {
  driver: "Driver",
  front_right: "Front passenger",
  rear_left: "Rear left",
  rear_right: "Rear right",
  rear_center: "Rear center",
};

export function CabinPanel() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CabinOccupancy | null>(null);

  const onFile = async (file: File | null) => {
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    try {
      const data = await analyzeCabinFrame(file, file.name);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cabin analysis failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">
            Cabin intelligence
          </h2>
          <p className="text-sm text-slate-400">
            Seat occupancy, child heuristic, unattended vehicle (Module 02)
          </p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() => fileRef.current?.click()}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {busy ? "Analyzing…" : "Upload cabin frame"}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png"
          className="hidden"
          onChange={(e) => void onFile(e.target.files?.[0] ?? null)}
        />
      </div>

      {error ? (
        <p className="mb-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Stat label="Occupants" value={String(result.total_occupants)} />
            <Stat
              label="Child alert"
              value={result.child_alert ? "Yes" : "No"}
              danger={result.child_alert}
            />
            <Stat
              label="Unattended"
              value={result.unattended_vehicle ? "Yes" : "No"}
              danger={result.unattended_vehicle}
            />
            <Stat
              label="Model"
              value={result.model_loaded ? "YOLO loaded" : "Fallback"}
            />
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(result.occupant_map).map(([zone, occupied]) => (
              <div
                key={zone}
                className={`rounded-lg border px-3 py-2 text-sm ${
                  occupied
                    ? "border-emerald-500/40 bg-emerald-950/40 text-emerald-100"
                    : "border-slate-700 bg-slate-950/50 text-slate-500"
                }`}
              >
                {SEAT_LABELS[zone] || zone}: {occupied ? "Occupied" : "Empty"}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-500">
          Upload an interior cabin image to detect seat zones and occupancy.
        </p>
      )}
    </section>
  );
}

function Stat({
  label,
  value,
  danger,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border px-3 py-2 ${
        danger
          ? "border-red-500/40 bg-red-950/40"
          : "border-slate-700 bg-slate-950/50"
      }`}
    >
      <p className="text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </p>
      <p className="text-sm font-semibold text-slate-100">{value}</p>
    </div>
  );
}
