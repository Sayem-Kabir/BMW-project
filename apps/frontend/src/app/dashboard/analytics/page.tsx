"use client";

import Link from "next/link";
import { LeaderboardPanel } from "@/components/fleet/LeaderboardPanel";

export default function AnalyticsPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 bg-slate-900/50">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-violet-300">
              Phase 6 · Module 6D
            </p>
            <h1 className="text-2xl font-bold">Fleet Analytics</h1>
            <p className="text-sm text-slate-400">
              Driver leaderboard and weekly incident trends
            </p>
          </div>
          <nav className="flex flex-wrap gap-3 text-sm">
            <Link href="/dashboard" className="text-slate-400 hover:text-white">
              Dashboard
            </Link>
            <Link
              href="/dashboard/alerts"
              className="text-slate-400 hover:text-white"
            >
              Alerts
            </Link>
            <Link href="/safety" className="text-slate-400 hover:text-white">
              Safety
            </Link>
          </nav>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-6 py-8">
        <LeaderboardPanel />
      </div>
    </main>
  );
}
