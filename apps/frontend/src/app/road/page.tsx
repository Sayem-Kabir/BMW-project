import Link from "next/link";
import { RoadMonitor } from "@/components/road/RoadMonitor";

export default function RoadUnderstandingPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 bg-slate-900/50">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-blue-300">
              Phase 2 · Module 2I
            </p>
            <h1 className="text-2xl font-bold">Road Understanding</h1>
          </div>
          <nav className="flex gap-4 text-sm">
            <Link href="/" className="text-slate-400 hover:text-white">
              Home
            </Link>
            <Link href="/monitor" className="text-slate-400 hover:text-white">
              Driver
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
            Live road frames flow through DeepLabV3+ segmentation, YOLO and
            ByteTrack, MiDaS depth, traffic-light classification, and Caltech
            temporal pedestrian localization.
          </p>
        </div>
        <RoadMonitor />
      </div>
    </main>
  );
}
