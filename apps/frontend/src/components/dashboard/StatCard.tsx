"use client";

import type { ReactNode } from "react";

export function StatCard({
  label,
  value,
  hint,
  accent = "sky",
}: {
  label: string;
  value: string | number;
  hint?: string;
  accent?: "sky" | "emerald" | "amber" | "fuchsia" | "rose";
}) {
  const accents = {
    sky: "text-sky-300",
    emerald: "text-emerald-300",
    amber: "text-amber-300",
    fuchsia: "text-fuchsia-300",
    rose: "text-rose-300",
  };
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
      <p className="text-sm text-slate-400">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${accents[accent]}`}>{value}</p>
      {hint ? <p className="mt-2 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}
