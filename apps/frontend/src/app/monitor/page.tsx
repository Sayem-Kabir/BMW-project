"use client";

import dynamic from "next/dynamic";
import { RoleShell } from "@/components/dashboard/RoleShell";

const DriverMonitor = dynamic(
  () => import("@/components/driver/DriverMonitor").then((m) => m.DriverMonitor),
  { ssr: false, loading: () => <div className="h-64 animate-pulse rounded-xl bg-slate-800" /> }
);

const CabinPanel = dynamic(
  () => import("@/components/cabin/CabinPanel").then((m) => m.CabinPanel),
  { ssr: false, loading: () => <div className="h-48 animate-pulse rounded-xl bg-slate-800" /> }
);

export default function MonitorPage() {
  return (
    <RoleShell subtitle="Live cabin feed — EAR/MAR, head pose, YOLO, alertness">
      <div className="space-y-6">
        <DriverMonitor />
        <CabinPanel />
      </div>
    </RoleShell>
  );
}
