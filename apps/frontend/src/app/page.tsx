import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-bmw-blue to-blue-900">
      <div className="text-center px-6">
        <p className="text-sm uppercase tracking-widest text-blue-200 mb-3">Phase 0 complete</p>
        <h1 className="text-5xl font-bold mb-4">
          BMW AI Automotive Intelligence Platform
        </h1>
        <p className="text-xl text-gray-300 mb-8 max-w-2xl mx-auto">
          Real-time Driver Monitoring • Road Understanding • Predictive Maintenance
        </p>
        <div className="space-x-4">
          <Link
            href="/dashboard"
            className="inline-block px-8 py-3 bg-white text-bmw-blue font-bold rounded-lg hover:bg-gray-200"
          >
            Dashboard
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
