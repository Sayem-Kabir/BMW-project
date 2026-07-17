export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white p-8">
      <h1 className="text-3xl font-bold mb-2">Fleet Dashboard</h1>
      <p className="text-slate-400 mb-8">
        Phase 0 scaffold — real-time fleet UI ships in Phase 6.
      </p>
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
