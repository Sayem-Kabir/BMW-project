import Link from "next/link";
import { MaintenanceDashboard } from "@/components/maintenance/MaintenanceDashboard";

export default function MaintenancePage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 bg-slate-900/50">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-blue-300">
              Phase 3 · Module 3I
            </p>
            <h1 className="text-2xl font-bold">Predictive Maintenance</h1>
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
            <Link href="/dashboard" className="text-slate-400 hover:text-white">
              Dashboard
            </Link>
            <Link href="/safety" className="text-slate-400 hover:text-white">
              Safety
            </Link>
            <Link href="/assistant" className="text-slate-400 hover:text-white">
              Assistant
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
            Monitor engine, brake, battery, and tire health from the unified 3G
            pipeline. Review maintenance alerts, persisted trends, and native
            XGBoost feature contributions for every available component.
          </p>
        </div>
        <MaintenanceDashboard />
      </div>
    </main>
  );
}
