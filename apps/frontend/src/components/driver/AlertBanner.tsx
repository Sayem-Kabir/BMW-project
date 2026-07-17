"use client";

import type { RiskLevel } from "@/lib/types";

interface AlertBannerProps {
  risk: RiskLevel;
  message: string;
}

export function AlertBanner({ risk, message }: AlertBannerProps) {
  if (risk !== "HIGH" && risk !== "CRITICAL") return null;

  const tone =
    risk === "CRITICAL"
      ? "border-red-500/60 bg-red-950/80 text-red-100"
      : "border-orange-500/60 bg-orange-950/80 text-orange-100";

  return (
    <div
      role="alert"
      className={`absolute left-4 right-4 top-4 z-20 rounded-md border px-4 py-3 text-sm font-medium shadow-lg backdrop-blur-sm ${tone}`}
    >
      <span className="mr-2 font-semibold tracking-wide">{risk}</span>
      {message}
    </div>
  );
}
