"use client";

import type { RiskLevel } from "@/lib/types";

const RISK_COLOR: Record<RiskLevel, string> = {
  LOW: "#22c55e",
  MEDIUM: "#eab308",
  HIGH: "#f97316",
  CRITICAL: "#ef4444",
};

interface RiskGaugeProps {
  score: number;
  risk: RiskLevel;
}

/** Compact circular alertness gauge for the live monitor HUD. */
export function RiskGauge({ score, risk }: RiskGaugeProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const color = RISK_COLOR[risk] ?? RISK_COLOR.LOW;
  const circumference = 2 * Math.PI * 42;
  const offset = circumference * (1 - clamped / 100);

  return (
    <div className="relative flex h-28 w-28 items-center justify-center">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100" aria-hidden>
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke="rgba(148,163,184,0.25)"
          strokeWidth="8"
        />
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-300"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-semibold tabular-nums">{clamped}</span>
        <span className="text-[10px] uppercase tracking-wider text-slate-400">{risk}</span>
      </div>
    </div>
  );
}
