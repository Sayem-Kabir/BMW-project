export default function MaintenanceLoading() {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <header className="border-b border-[var(--border)] bg-[var(--surface)]">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="space-y-2">
            <div className="h-3 w-24 animate-pulse rounded bg-slate-700" />
            <div className="h-7 w-40 animate-pulse rounded bg-slate-700" />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl space-y-6 px-6 py-8">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="h-40 animate-pulse rounded-lg bg-slate-800" />
          <div className="h-40 animate-pulse rounded-lg bg-slate-800" />
        </div>
        <div className="h-56 animate-pulse rounded-xl bg-slate-800" />
      </main>
    </div>
  );
}
