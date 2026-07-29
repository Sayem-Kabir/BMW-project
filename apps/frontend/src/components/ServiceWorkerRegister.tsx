"use client";

import { useEffect } from "react";

/** Spec Phase 12B — register service worker for installable driver PWA. */
export function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* ignore SW failures in dev */
    });
  }, []);
  return null;
}
