import Link from "next/link";
import { DriverMonitor } from "@/components/driver/DriverMonitor";

export default function MonitorPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 bg-slate-900/50">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-blue-300">Phase 1 · Module 1G</p>
            <h1 className="text-2xl font-bold text-white">Driver Monitor</h1>
          </div>
          <nav className="flex gap-3 text-sm">
            <Link href="/" className="text-slate-400 hover:text-white">
              Home
            </Link>
            <Link href="/dashboard" className="text-slate-400 hover:text-white">
              Dashboard
            </Link>
            <Link href="/road" className="text-slate-400 hover:text-white">
              Road
            </Link>
            <Link
              href="/maintenance"
              className="text-slate-400 hover:text-white"
            >
              Maintenance
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

      <div className="mx-auto max-w-6xl px-6 py-8">
        <p className="mb-6 max-w-2xl text-slate-400">
          Live cabin feed → WebSocket frames → EAR/MAR, head pose, and YOLO detections with
          alertness scoring.
        </p>
        <DriverMonitor />
      </div>
    </main>
  );
}
