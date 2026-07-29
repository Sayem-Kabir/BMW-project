"use client";

import {
  createContext,
  useContext,
  type ReactNode,
} from "react";
import { normalizeAppRole, type AppRole } from "@/lib/roles";

const RoleContext = createContext<AppRole | null>(null);

/** Server layout reads `bmw_role` cookie and provides it here for SSR/client match. */
export function RoleProvider({
  role,
  children,
}: {
  role?: string | null;
  children: ReactNode;
}) {
  const value =
    role != null && String(role).trim() !== ""
      ? normalizeAppRole(role)
      : null;
  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
}

export function useServerRole(): AppRole | null {
  return useContext(RoleContext);
}
