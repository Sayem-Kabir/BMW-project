import Link from "next/link";

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white p-8">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2">Fleet Dashboard</h1>
          <p className="text-slate-400">
            Fleet overview scaffold — driver and road intelligence are live.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/monitor"
            className="rounded-lg border border-slate-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800"
          >
            Driver monitor
          </Link>
          <Link
            href="/road"
            className="rounded-lg bg-bmw-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-800"
          >
            Road understanding
          </Link>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-6">
          <p className="text-sm text-slate-400">Vehicles</p>
          <p className="text-2xl font-semibold">—</p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-6">
          <p className="text-sm text-slate-400">Active alerts</p>
          <p className="text-2xl font-semibold">—</p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-6">
          <p className="text-sm text-slate-400">Avg risk</p>
          <p className="text-2xl font-semibold">—</p>
        </div>
      </div>
    </main>
  );
}
