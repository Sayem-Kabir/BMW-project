"use client";

import dynamic from "next/dynamic";
import { RoleShell } from "@/components/dashboard/RoleShell";

const RoadMonitor = dynamic(
  () => import("@/components/road/RoadMonitor").then((m) => m.RoadMonitor),
  { ssr: false, loading: () => <div className="aspect-video w-full animate-pulse rounded-xl bg-slate-800" /> }
);

export default function RoadUnderstandingPage() {
  return (
    <RoleShell subtitle="Road segmentation, tracking, depth, and pedestrian risk">
      <RoadMonitor />
    </RoleShell>
  );
}
