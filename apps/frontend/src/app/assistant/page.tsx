"use client";

import { Suspense } from "react";
import { RoleShell } from "@/components/dashboard/RoleShell";
import { AssistantChat } from "@/components/assistant/AssistantChat";

export default function AssistantPage() {
  return (
    <RoleShell subtitle="RAG assistant over manuals, OBD, telemetry, and maintenance">
      <Suspense
        fallback={<p className="text-sm text-slate-500">Loading assistant…</p>}
      >
        <AssistantChat />
      </Suspense>
    </RoleShell>
  );
}
