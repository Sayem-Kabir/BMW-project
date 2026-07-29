"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getMe, logout } from "@/lib/api";
import { clearRoleCookie } from "@/lib/roles";

export function AuthStatus() {
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null;
    if (!token) {
      setEmail(null);
      return;
    }
    getMe()
      .then((user) => {
        if (!cancelled) setEmail(user.email);
      })
      .catch(() => {
        if (!cancelled) setEmail(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!email) {
    return (
      <Link href="/login" className="text-slate-400 hover:text-white">
        Login
      </Link>
    );
  }

  return (
    <span className="flex items-center gap-2 text-xs text-slate-400">
      <span className="hidden sm:inline truncate max-w-[140px]" title={email}>
        {email}
      </span>
      <Link
        href="/settings/security"
        className="hidden sm:inline text-[11px] text-slate-500 hover:text-slate-200"
      >
        Security
      </Link>
      <button
        type="button"
        onClick={() => {
          logout();
          clearRoleCookie();
          setEmail(null);
          window.location.href = "/";
        }}
        className="rounded-lg border border-slate-700 px-2 py-0.5 text-[11px] text-slate-200 hover:bg-slate-800"
      >
        Logout
      </button>
    </span>
  );
}
