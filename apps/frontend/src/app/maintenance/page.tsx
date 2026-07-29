"use client";

import { RoleShell } from "@/components/dashboard/RoleShell";
import { MaintenanceDashboard } from "@/components/maintenance/MaintenanceDashboard";

export default function MaintenancePage() {
  return (
    <RoleShell subtitle="Engine, brake, battery, and tire health predictions">
      <MaintenanceDashboard />
    </RoleShell>
  );
}
