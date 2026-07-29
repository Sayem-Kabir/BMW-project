"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { completeMfa, getMe, getGoogleAuthUrl, login } from "@/lib/api";
import { homePathForRole, setRoleCookie } from "@/lib/roles";

const DEMO_EMAIL = "demo@bmwai.dev";
const DEMO_PASSWORD = "demo1234";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [totp, setTotp] = useState("");
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const onGoogle = async () => {
    setError(null);
    try {
      const { authorization_url } = await getGoogleAuthUrl();
      window.location.href = authorization_url;
    } catch {
      setError("Google sign-in is not configured on this server.");
    }
  };

  const finishLogin = async () => {
    const me = await getMe();
    setRoleCookie(me.role);
    if (!me.org_id) {
      router.push("/onboarding");
      return;
    }
    router.push(homePathForRole(me.role));
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      if (mfaToken) {
        await completeMfa(mfaToken, totp);
        setMfaToken(null);
        await finishLogin();
        return;
      }
      const result = await login(email, password, totp || undefined);
      if (result.mfa_required && result.mfa_token) {
        setMfaToken(result.mfa_token);
        return;
      }
      await finishLogin();
    } catch (err: unknown) {
      const axiosMsg =
        err &&
        typeof err === "object" &&
        "response" in err &&
        err.response &&
        typeof err.response === "object" &&
        "data" in err.response
          ? (() => {
              const data = err.response.data as { detail?: unknown };
              if (typeof data?.detail === "string") return data.detail;
              if (Array.isArray(data?.detail) && data.detail[0]) {
                const first = data.detail[0] as { msg?: string };
                return first.msg || null;
              }
              return null;
            })()
          : null;
      setError(
        axiosMsg ||
          (err instanceof Error ? err.message : null) ||
          "Login failed — seed demo user with scripts/seed_safety_demo.py"
      );
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-white">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        <p className="text-xs uppercase tracking-widest text-sky-300">
          Spec Phase 8 · Auth
        </p>
        <h1 className="mt-1 text-2xl font-bold">Sign in</h1>
        <p className="mt-1 text-sm text-slate-400">
          Demo: <span className="font-mono text-slate-300">{DEMO_EMAIL}</span> /
          demo1234. Also admin@ / driver@ / tech@ / super@bmwai.dev
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {!mfaToken ? (
            <>
              <label className="block text-sm">
                <span className="mb-1 block text-slate-400">Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
                  required
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block text-slate-400">Password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
                  required
                />
              </label>
            </>
          ) : (
            <label className="block text-sm">
              <span className="mb-1 block text-slate-400">Authenticator code</span>
              <input
                type="text"
                inputMode="numeric"
                value={totp}
                onChange={(e) => setTotp(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
                required
                autoFocus
              />
            </label>
          )}
          {error ? (
            <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {error}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={pending}
            className="w-full rounded-xl bg-sky-600 px-4 py-2 text-sm font-semibold hover:bg-sky-500 disabled:opacity-50"
          >
            {pending ? "Signing in…" : mfaToken ? "Verify MFA" : "Sign in"}
          </button>
          <button
            type="button"
            onClick={() => void onGoogle()}
            className="w-full rounded-xl border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800"
          >
            Continue with Google
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-slate-500">
          <Link href="/register" className="text-sky-400 hover:text-sky-300">
            Create account
          </Link>
          {" · "}
          <Link href="/forgot-password" className="text-sky-400 hover:text-sky-300">
            Forgot password
          </Link>
          {" · "}
          <Link href="/dashboard" className="text-slate-400 hover:text-white">
            Continue without login
          </Link>
        </p>
      </div>
    </main>
  );
}
