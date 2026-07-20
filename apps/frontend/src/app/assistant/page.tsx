import Link from "next/link";
import { AssistantChat } from "@/components/assistant/AssistantChat";

export default function AssistantPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 bg-slate-900/50">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-sky-300">
              Phase 5 · Module 5E–5G
            </p>
            <h1 className="text-2xl font-bold">AI Vehicle Assistant</h1>
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
            <Link href="/safety" className="text-slate-400 hover:text-white">
              Risk &amp; Events
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
            RAG-grounded chat over the owner manual, OBD codes, and service
            intervals — with live/demo telemetry, predictive-maintenance state,
            multi-turn memory, and SSE streaming replies from Modules 5D–5G.
          </p>
        </div>
        <AssistantChat />
      </div>
    </main>
  );
}
