/** Spec Phase 9 — role cookie + home path (canonical roles via access matrix). */

export {
  type AppRole,
  type DashboardRole,
  type FeatureId,
  canAccess,
  canAccessPath,
  featuresForRole,
  homePathForRole,
  navLinksForRole,
  normalizeAppRole,
  normalizeDashboardRole,
  shellMetaForRole,
} from "./access";

import { normalizeAppRole } from "./access";

export function setRoleCookie(role: string) {
  if (typeof document === "undefined") return;
  const canonical = normalizeAppRole(role);
  document.cookie = `bmw_role=${canonical}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
}

export function clearRoleCookie() {
  if (typeof document === "undefined") return;
  document.cookie = "bmw_role=; path=/; max-age=0; SameSite=Lax";
}

export function readRoleCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )bmw_role=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}
