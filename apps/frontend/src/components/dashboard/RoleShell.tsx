"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { AuthStatus } from "@/components/AuthStatus";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useServerRole } from "@/components/dashboard/RoleProvider";
import {
  navLinksForRole,
  normalizeAppRole,
  readRoleCookie,
  shellMetaForRole,
  type AppRole,
} from "@/lib/roles";

export function RoleShell({
  role: roleProp,
  subtitle,
  children,
}: {
  /** Optional; defaults to server RoleProvider / bmw_role cookie. */
  role?: AppRole | string;
  subtitle?: string;
  children: ReactNode;
}) {
  const serverRole = useServerRole();

  // Prefer prop / server cookie (SSR-safe). Only read document.cookie after mount.
  const [role, setRole] = useState<AppRole>(() =>
    normalizeAppRole(roleProp || serverRole)
  );

  useEffect(() => {
    setRole(normalizeAppRole(roleProp || serverRole || readRoleCookie()));
  }, [roleProp, serverRole]);

  const meta = shellMetaForRole(role);
  const links = navLinksForRole(role);

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <header
        className="border-b border-[var(--border)] bg-[var(--surface)]"
        role="banner"
      >
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <div>
            <p
              className={`text-xs uppercase tracking-widest ${meta.accent}`}
              suppressHydrationWarning
            >
              {meta.eyebrow}
            </p>
            <h1 className="text-2xl font-bold" suppressHydrationWarning>
              {meta.title}
            </h1>
            {subtitle ? (
              <p className="text-sm text-[var(--muted)]">{subtitle}</p>
            ) : null}
          </div>
          <nav
            className="flex flex-wrap items-center gap-3 text-sm"
            aria-label="Primary"
            suppressHydrationWarning
          >
            {links.map((link) =>
              link.external ? (
                <a
                  key={link.href}
                  href={link.href}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[var(--muted)] hover:text-[var(--fg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                >
                  {link.label}
                </a>
              ) : (
                <Link
                  key={link.href}
                  href={link.href}
                  prefetch={true}
                  className="text-[var(--muted)] hover:text-[var(--fg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                >
                  {link.label}
                </Link>
              )
            )}
            <ThemeToggle />
            <AuthStatus />
          </nav>
        </div>
      </header>
      <main
        id="main-content"
        className="mx-auto max-w-7xl space-y-6 px-6 py-8"
        tabIndex={-1}
      >
        {children}
      </main>
    </div>
  );
}
