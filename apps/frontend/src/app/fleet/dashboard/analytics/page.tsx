"use client";

import { LeaderboardPanel } from "@/components/fleet/LeaderboardPanel";
import { RoleShell } from "@/components/dashboard/RoleShell";

export default function FleetAnalyticsPage() {
  return (
    <RoleShell subtitle="Driver leaderboard and weekly incident trends">
      <LeaderboardPanel />
    </RoleShell>
  );
}
