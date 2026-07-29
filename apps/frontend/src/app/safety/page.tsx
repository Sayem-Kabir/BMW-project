"use client";

import { RoleShell } from "@/components/dashboard/RoleShell";
import { SafetyDashboard } from "@/components/safety/SafetyDashboard";

export default function SafetyPage() {
  return (
    <RoleShell subtitle="Composite risk, trends, and acknowledgeable safety events">
      <SafetyDashboard />
    </RoleShell>
  );
}
