"use client";

import { AlertsCenter } from "@/components/fleet/AlertsCenter";
import { RoleShell } from "@/components/dashboard/RoleShell";

export default function FleetAlertsPage() {
  return (
    <RoleShell subtitle="Acknowledge safety alerts, clips, and XAI previews">
      <AlertsCenter />
    </RoleShell>
  );
}
