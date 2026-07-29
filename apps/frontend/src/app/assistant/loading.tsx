export default function AssistantLoading() {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <header className="border-b border-[var(--border)] bg-[var(--surface)]">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="space-y-2">
            <div className="h-3 w-24 animate-pulse rounded bg-slate-700" />
            <div className="h-7 w-32 animate-pulse rounded bg-slate-700" />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="h-96 animate-pulse rounded-xl bg-slate-800" />
      </main>
    </div>
  );
}
