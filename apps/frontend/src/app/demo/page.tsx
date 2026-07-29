"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RoleShell } from "@/components/dashboard/RoleShell";
import { getDemoStatus, startDemo, stopDemo } from "@/lib/api";

export default function DemoModePage() {
  const queryClient = useQueryClient();
  const statusQuery = useQuery({
    queryKey: ["demo-status"],
    queryFn: getDemoStatus,
    refetchInterval: 2000,
  });

  const startMutation = useMutation({
    mutationFn: (opts?: { max_frames?: number; loop?: boolean }) =>
      startDemo({
        synthetic_only: true,
        loop: opts?.loop ?? true,
        fps: 4,
        max_frames: opts?.max_frames,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["demo-status"] }),
  });
  const stopMutation = useMutation({
    mutationFn: stopDemo,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["demo-status"] }),
  });

  const status = statusQuery.data;
  const running = Boolean(status?.running);

  return (
    <RoleShell subtitle="Replay synthetic frames into live APIs — no car required">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-slate-400">Status</p>
            <p className="text-2xl font-semibold">
              {running ? (
                <span className="text-amber-300">Running</span>
              ) : (
                status?.status || "Idle"
              )}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {status?.pid ? `pid=${status.pid} · ` : ""}
              vehicle={status?.vehicle_id || "—"}
              {status?.phase ? ` · phase=${status.phase}` : ""}
              {status?.started_at
                ? ` · started=${new Date(status.started_at).toLocaleTimeString()}`
                : ""}
            </p>
            {status?.last_error ? (
              <p className="mt-2 max-w-xl truncate text-xs text-red-300">
                {status.last_error}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={running || startMutation.isPending}
              onClick={() =>
                startMutation.mutate({ max_frames: 30, loop: false })
              }
              className="rounded-xl border border-amber-500/40 px-4 py-2 text-sm font-semibold text-amber-100 hover:bg-amber-500/10 disabled:opacity-50"
            >
              Quick run (30 frames)
            </button>
            <button
              type="button"
              disabled={running || startMutation.isPending}
              onClick={() => startMutation.mutate({ loop: true })}
              className="rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold hover:bg-amber-500 disabled:opacity-50"
            >
              {startMutation.isPending ? "Starting…" : "Start loop"}
            </button>
            <button
              type="button"
              disabled={!running || stopMutation.isPending}
              onClick={() => stopMutation.mutate()}
              className="rounded-xl border border-slate-600 px-4 py-2 text-sm font-semibold hover:bg-slate-800 disabled:opacity-50"
            >
              {stopMutation.isPending ? "Stopping…" : "Stop"}
            </button>
          </div>
        </div>
        {startMutation.isError || stopMutation.isError ? (
          <p className="mt-4 text-sm text-red-300">
            Demo control request failed — is the backend on :8000?
          </p>
        ) : null}
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="mb-3 text-sm font-semibold">Suggested walkthrough</h2>
        <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-300">
          <li>
            Click <span className="text-amber-200">Quick run</span> or{" "}
            <span className="text-amber-200">Start loop</span>.
          </li>
          <li>
            Open{" "}
            <Link
              href="/fleet/dashboard"
              className="text-amber-300 hover:underline"
            >
              Fleet dashboard
            </Link>{" "}
            — risk cards and alerts update.
          </li>
          <li>
            Open{" "}
            <Link href="/safety" className="text-amber-300 hover:underline">
              Safety
            </Link>{" "}
            for live risk gauge / events.
          </li>
          <li>
            Ask the{" "}
            <Link href="/assistant" className="text-amber-300 hover:underline">
              assistant
            </Link>{" "}
            about TPMS or P0420.
          </li>
        </ol>
      </section>
    </RoleShell>
  );
}
