import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-bmw-blue to-blue-900">
      <div className="text-center px-6">
        <p className="text-sm uppercase tracking-widest text-blue-200 mb-3">
          Live driver + road intelligence
        </p>
        <h1 className="text-5xl font-bold mb-4">
          BMW AI Automotive Intelligence Platform
        </h1>
        <p className="text-xl text-gray-300 mb-8 max-w-2xl mx-auto">
          Real-time Driver Monitoring • Road Understanding • Predictive Maintenance • Risk & Events • AI Assistant
        </p>
        <div className="space-x-4">
          <Link
            href="/monitor"
            className="inline-block px-8 py-3 bg-white text-bmw-blue font-bold rounded-lg hover:bg-gray-200"
          >
            Live Monitor
          </Link>
          <Link
            href="/dashboard"
            className="inline-block px-8 py-3 bg-bmw-blue border-2 border-white text-white font-bold rounded-lg hover:bg-blue-800"
          >
            Dashboard
          </Link>
          <Link
            href="/road"
            className="inline-block px-8 py-3 bg-emerald-600 border-2 border-emerald-300 text-white font-bold rounded-lg hover:bg-emerald-500"
          >
            Road View
          </Link>
          <Link
            href="/maintenance"
            className="inline-block px-8 py-3 bg-violet-700 border-2 border-violet-300 text-white font-bold rounded-lg hover:bg-violet-600"
          >
            Maintenance
          </Link>
          <Link
            href="/safety"
            className="inline-block px-8 py-3 bg-orange-700 border-2 border-orange-300 text-white font-bold rounded-lg hover:bg-orange-600"
          >
            Risk & Events
          </Link>
          <Link
            href="/assistant"
            className="inline-block px-8 py-3 bg-sky-700 border-2 border-sky-300 text-white font-bold rounded-lg hover:bg-sky-600"
          >
            AI Assistant
          </Link>
          <a
            href="http://localhost:8000/docs"
            className="inline-block px-8 py-3 bg-bmw-blue border-2 border-white text-white font-bold rounded-lg hover:bg-blue-800"
            target="_blank"
            rel="noreferrer"
          >
            API Docs
          </a>
        </div>
      </div>
    </main>
  );
}
