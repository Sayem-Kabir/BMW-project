"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { verifyEmail } from "@/lib/api";

function VerifyEmailInner() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token")?.trim() || "";
  const [status, setStatus] = useState<"idle" | "ok" | "fail">("idle");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    verifyEmail(token)
      .then(() => {
        if (!cancelled) {
          setStatus("ok");
          setMessage("Email verified — you can sign in now.");
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setStatus("fail");
          setMessage(
            err instanceof Error ? err.message : "Verification failed"
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-white">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-center">
        <h1 className="text-2xl font-bold">Verify email</h1>
        {!token ? (
          <p className="mt-4 text-sm text-slate-400">
            Missing token. Check your verification email link.
          </p>
        ) : status === "idle" ? (
          <p className="mt-4 text-sm text-slate-400">Verifying…</p>
        ) : (
          <p
            className={`mt-4 text-sm ${
              status === "ok" ? "text-emerald-300" : "text-red-300"
            }`}
          >
            {message}
          </p>
        )}
        <Link
          href="/login"
          className="mt-6 inline-block text-sky-400 hover:text-sky-300"
        >
          Back to sign in
        </Link>
      </div>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<p className="p-8 text-slate-400">Loading…</p>}>
      <VerifyEmailInner />
    </Suspense>
  );
}
