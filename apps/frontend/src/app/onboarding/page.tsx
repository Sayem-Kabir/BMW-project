"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { createOnboardingOrg, getMe } from "@/lib/api";
import { homePathForRole, setRoleCookie } from "@/lib/roles";

export default function OnboardingPage() {
  const router = useRouter();
  const [orgName, setOrgName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await createOnboardingOrg(orgName);
      const me = await getMe();
      setRoleCookie(me.role);
      router.push(homePathForRole(me.role));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not create organization");
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-white">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        <p className="text-xs uppercase tracking-widest text-amber-300">
          Spec Phase 8E
        </p>
        <h1 className="mt-1 text-2xl font-bold">Set up your organization</h1>
        <p className="mt-2 text-sm text-slate-400">
          Empty-state onboarding — create an org to unlock the fleet dashboard.
        </p>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Organization name</span>
            <input
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              minLength={2}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
              required
            />
          </label>
          {error ? (
            <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {error}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={pending}
            className="w-full rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold hover:bg-amber-500 disabled:opacity-50"
          >
            {pending ? "Saving…" : "Continue to dashboard"}
          </button>
        </form>
        <p className="mt-4 text-center text-xs text-slate-500">
          <Link href="/dashboard" className="text-slate-400 hover:text-white">
            Skip for now
          </Link>
        </p>
      </div>
    </main>
  );
}
