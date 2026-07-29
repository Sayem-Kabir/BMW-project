"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  confirmMfa,
  disableMfa,
  enableMfa,
  getMe,
} from "@/lib/api";
import { RoleShell } from "@/components/dashboard/RoleShell";

export default function SecuritySettingsPage() {
  const [mfaEnabled, setMfaEnabled] = useState(false);
  const [otpauthUrl, setOtpauthUrl] = useState<string | null>(null);
  const [secret, setSecret] = useState<string | null>(null);
  const [totp, setTotp] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    getMe()
      .then((u) => setMfaEnabled(Boolean(u.mfa_enabled)))
      .catch(() => undefined);
  }, []);

  const startMfa = async () => {
    setPending(true);
    setError(null);
    try {
      const data = await enableMfa();
      setSecret(data.secret);
      setOtpauthUrl(data.otpauth_url);
      setMessage("Scan the OTP URI in your authenticator app, then enter a code.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start MFA");
    } finally {
      setPending(false);
    }
  };

  const confirmSetup = async (e: FormEvent) => {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      await confirmMfa(totp);
      setMfaEnabled(true);
      setMessage("MFA enabled.");
      setSecret(null);
      setOtpauthUrl(null);
      setTotp("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid code");
    } finally {
      setPending(false);
    }
  };

  const turnOffMfa = async (e: FormEvent) => {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      await disableMfa(totp);
      setMfaEnabled(false);
      setMessage("MFA disabled.");
      setTotp("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not disable MFA");
    } finally {
      setPending(false);
    }
  };

  return (
    <RoleShell subtitle="TOTP MFA and account security (Spec Phase 8F)">
      <section className="max-w-lg rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-lg font-semibold">Multi-factor authentication</h2>
        <p className="mt-1 text-sm text-slate-400">
          Status: {mfaEnabled ? "Enabled" : "Disabled"}
        </p>

        {message ? (
          <p className="mt-3 text-sm text-emerald-300">{message}</p>
        ) : null}
        {error ? (
          <p className="mt-3 text-sm text-red-300">{error}</p>
        ) : null}

        {!mfaEnabled && !secret ? (
          <button
            type="button"
            disabled={pending}
            onClick={() => void startMfa()}
            className="mt-4 rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
          >
            Enable MFA
          </button>
        ) : null}

        {secret && otpauthUrl ? (
          <form onSubmit={confirmSetup} className="mt-4 space-y-3">
            <p className="break-all text-xs text-slate-500">{otpauthUrl}</p>
            <p className="text-xs text-slate-400">Secret: {secret}</p>
            <input
              value={totp}
              onChange={(e) => setTotp(e.target.value)}
              placeholder="6-digit code"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            />
            <button
              type="submit"
              disabled={pending}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white"
            >
              Confirm MFA
            </button>
          </form>
        ) : null}

        {mfaEnabled ? (
          <form onSubmit={turnOffMfa} className="mt-6 space-y-3 border-t border-slate-800 pt-4">
            <p className="text-sm text-slate-400">Disable MFA</p>
            <input
              value={totp}
              onChange={(e) => setTotp(e.target.value)}
              placeholder="Current TOTP code"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            />
            <button
              type="submit"
              disabled={pending}
              className="rounded-lg border border-red-500/50 px-4 py-2 text-sm text-red-200"
            >
              Disable MFA
            </button>
          </form>
        ) : null}

        <Link href="/driver/dashboard" className="mt-6 inline-block text-sm text-sky-400">
          ← Back to dashboard
        </Link>
      </section>
    </RoleShell>
  );
}
