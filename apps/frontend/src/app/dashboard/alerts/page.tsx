"use client";

import Link from "next/link";
import { AlertsCenter } from "@/components/fleet/AlertsCenter";

export default function AlertsPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 bg-slate-900/50">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-orange-300">
              Phase 6 · Module 6E
            </p>
            <h1 className="text-2xl font-bold">Fleet Alerts Center</h1>
            <p className="text-sm text-slate-400">
              Acknowledge safety alerts, open clips, and preview XAI explanations
            </p>
          </div>
          <nav className="flex flex-wrap gap-3 text-sm">
            <Link href="/dashboard" className="text-slate-400 hover:text-white">
              Dashboard
            </Link>
            <Link
              href="/dashboard/analytics"
              className="text-slate-400 hover:text-white"
            >
              Analytics
            </Link>
            <Link href="/safety" className="text-slate-400 hover:text-white">
              Safety
            </Link>
          </nav>
        </div>
      </header>
      <div className="mx-auto max-w-5xl px-6 py-8">
        <AlertsCenter />
      </div>
    </main>
  );
}
