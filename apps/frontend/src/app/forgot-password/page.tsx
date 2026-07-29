"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { requestPasswordReset } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setPending(true);
    setMessage(null);
    try {
      const data = await requestPasswordReset(email);
      let text = "If the account exists, a reset link was sent.";
      if (data.reset_token) {
        text += ` Dev token: ${data.reset_token}`;
      }
      setMessage(text);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Request failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-white">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        <h1 className="text-2xl font-bold">Forgot password</h1>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
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
          {message ? <p className="text-sm text-slate-300">{message}</p> : null}
          <button
            type="submit"
            disabled={pending}
            className="w-full rounded-lg bg-sky-600 py-2 font-semibold hover:bg-sky-500 disabled:opacity-50"
          >
            {pending ? "Sending…" : "Send reset link"}
          </button>
        </form>
        <Link href="/login" className="mt-4 block text-center text-sm text-sky-400">
          Back to sign in
        </Link>
      </div>
    </main>
  );
}
