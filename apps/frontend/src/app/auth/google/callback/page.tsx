"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { exchangeGoogleCode, getMe } from "@/lib/api";
import { homePathForRole, setRoleCookie } from "@/lib/roles";

function GoogleCallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const code = params.get("code");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!code) {
      setError("Missing Google authorization code");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        await exchangeGoogleCode(code);
        const me = await getMe();
        setRoleCookie(me.role);
        if (!cancelled) {
          router.replace(
            me.org_id ? homePathForRole(me.role) : "/onboarding"
          );
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Google sign-in failed");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code, router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
      <p className="text-sm text-slate-400">
        {error || "Completing Google sign-in…"}
      </p>
    </main>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={<p className="p-8 text-slate-400">Loading…</p>}>
      <GoogleCallbackInner />
    </Suspense>
  );
}
