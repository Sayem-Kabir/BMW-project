import Link from "next/link";
import { SafetyDashboard } from "@/components/safety/SafetyDashboard";

export default function SafetyPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 bg-slate-900/50">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-orange-300">
              Phase 4 · Module 4G
            </p>
            <h1 className="text-2xl font-bold">Risk &amp; Safety Events</h1>
          </div>
          <nav className="flex flex-wrap gap-4 text-sm">
            <Link href="/" className="text-slate-400 hover:text-white">
              Home
            </Link>
            <Link href="/monitor" className="text-slate-400 hover:text-white">
              Driver
            </Link>
            <Link href="/road" className="text-slate-400 hover:text-white">
              Road
            </Link>
            <Link href="/maintenance" className="text-slate-400 hover:text-white">
              Maintenance
            </Link>
            <Link href="/assistant" className="text-slate-400 hover:text-white">
              Assistant
            </Link>
            <Link href="/dashboard" className="text-slate-400 hover:text-white">
              Dashboard
            </Link>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="text-slate-400 hover:text-white"
            >
              API
            </a>
          </nav>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-7 max-w-3xl">
          <p className="text-slate-400">
            Live composite risk from the fleet WebSocket, persisted score trends,
            and an acknowledgeable safety event feed with XAI explanations and
            MinIO clip links.
          </p>
        </div>
        <SafetyDashboard />
      </div>
    </main>
  );
}
