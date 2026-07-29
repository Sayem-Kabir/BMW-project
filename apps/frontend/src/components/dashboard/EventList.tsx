"use client";

export type EventListItem = {
  id: string;
  event_type?: string;
  severity?: string;
  timestamp?: string | null;
  vehicle_id?: string;
};

export function EventList({
  events,
  emptyLabel = "No safety events",
}: {
  events: EventListItem[];
  emptyLabel?: string;
}) {
  if (!events.length) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 text-sm text-slate-500">
        {emptyLabel}
      </div>
    );
  }

  return (
    <ul className="divide-y divide-slate-800 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
      {events.map((event) => {
        const sev = String(event.severity || "LOW").toUpperCase();
        const tone =
          sev === "CRITICAL" || sev === "HIGH"
            ? "text-rose-300"
            : sev === "MEDIUM"
              ? "text-amber-300"
              : "text-sky-300";
        return (
          <li key={event.id} className="flex items-start justify-between gap-3 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-slate-100">
                {event.event_type || "event"}
              </p>
              <p className="text-xs text-slate-500">
                {event.timestamp
                  ? new Date(event.timestamp).toLocaleString()
                  : "—"}
              </p>
            </div>
            <span className={`text-xs font-semibold uppercase ${tone}`}>{sev}</span>
          </li>
        );
      })}
    </ul>
  );
}
