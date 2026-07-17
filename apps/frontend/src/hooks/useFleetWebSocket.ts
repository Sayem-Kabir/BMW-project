"use client";

import { useEffect, useState } from "react";
import { getFleetOverview } from "@/lib/api";
import type { FleetOverview } from "@/lib/types";
import { useAppStore } from "@/lib/store";

/** Polls fleet overview — replace with WebSocket in Phase 6. */
export function useFleetWebSocket(_orgId?: string) {
  const [connected, setConnected] = useState(false);
  const setFleetOverview = useAppStore((s) => s.setFleetOverview);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = (await getFleetOverview()) as FleetOverview;
        if (!cancelled) {
          setFleetOverview(data);
          setConnected(true);
        }
      } catch {
        if (!cancelled) setConnected(false);
      }
    }
    load();
    const id = setInterval(load, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [setFleetOverview]);

  return { connected };
}
