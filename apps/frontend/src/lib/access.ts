/**
 * Role → feature capability matrix.
 * Keep in sync with apps/backend/app/core/access.py
 */

export type AppRole =
  | "driver"
  | "maintenance_tech"
  | "fleet_manager"
  | "org_admin"
  | "super_admin";

export type FeatureId =
  | "home.driver"
  | "home.fleet"
  | "home.admin"
  | "demo"
  | "monitor"
  | "road"
  | "maintenance"
  | "safety"
  | "assistant"
  | "api_docs";

export const ROLE_FEATURES: Record<AppRole, FeatureId[]> = {
  driver: ["home.driver", "monitor", "road", "safety", "assistant"],
  maintenance_tech: ["home.fleet", "maintenance", "assistant"],
  fleet_manager: [
    "home.fleet",
    "demo",
    "monitor",
    "road",
    "maintenance",
    "safety",
    "assistant",
  ],
  org_admin: [
    "home.admin",
    "home.fleet",
    "demo",
    "maintenance",
    "safety",
    "assistant",
    "api_docs",
  ],
  super_admin: [
    "home.admin",
    "home.fleet",
    "demo",
    "maintenance",
    "safety",
    "assistant",
    "api_docs",
  ],
};

/** Nav links expanded per feature (fleet home includes sub-pages). */
export const FEATURE_LINKS: Record<
  FeatureId,
  Array<{ href: string; label: string; external?: boolean }>
> = {
  "home.driver": [{ href: "/driver/dashboard", label: "Home" }],
  "home.fleet": [
    { href: "/fleet/dashboard", label: "Fleet" },
    { href: "/fleet/dashboard/analytics", label: "Analytics" },
    { href: "/fleet/dashboard/alerts", label: "Alerts" },
    { href: "/fleet/dashboard/xai", label: "XAI" },
    { href: "/fleet/dashboard/twin", label: "Digital Twin" },
  ],
  "home.admin": [
    { href: "/admin/dashboard", label: "Admin" },
    { href: "/admin/dashboard/ota", label: "OTA Canary" },
  ],
  demo: [{ href: "/demo", label: "Demo Mode" }],
  monitor: [{ href: "/monitor", label: "Live Monitor" }],
  road: [{ href: "/road", label: "Road View" }],
  maintenance: [{ href: "/maintenance", label: "Maintenance" }],
  safety: [{ href: "/safety", label: "Risk & Events" }],
  assistant: [{ href: "/assistant", label: "AI Assistant" }],
  api_docs: [
    {
      href: "http://127.0.0.1:8001/docs",
      label: "API Docs",
      external: true,
    },
  ],
};

/** Path prefix → required feature */
const PATH_FEATURES: Array<{ prefix: string; feature: FeatureId }> = [
  { prefix: "/driver", feature: "home.driver" },
  { prefix: "/fleet", feature: "home.fleet" },
  { prefix: "/admin", feature: "home.admin" },
  { prefix: "/demo", feature: "demo" },
  { prefix: "/monitor", feature: "monitor" },
  { prefix: "/road", feature: "road" },
  { prefix: "/maintenance", feature: "maintenance" },
  { prefix: "/safety", feature: "safety" },
  { prefix: "/assistant", feature: "assistant" },
];

export function normalizeAppRole(role: string | null | undefined): AppRole {
  const r = (role || "").trim().toLowerCase();
  if (r === "driver" || r === "viewer") return "driver";
  if (r === "maintenance_tech") return "maintenance_tech";
  if (r === "fleet_manager" || r === "operator" || r === "fleet") {
    return "fleet_manager";
  }
  if (r === "org_admin" || r === "admin") return "org_admin";
  if (r === "super_admin") return "super_admin";
  return "fleet_manager";
}

export function featuresForRole(role: string | null | undefined): FeatureId[] {
  return ROLE_FEATURES[normalizeAppRole(role)];
}

export function canAccess(
  role: string | null | undefined,
  feature: FeatureId
): boolean {
  return featuresForRole(role).includes(feature);
}

export function featureForPath(pathname: string): FeatureId | null {
  const path = pathname.split("?")[0] || pathname;
  if (path === "/dashboard" || path.startsWith("/dashboard/")) {
    return "home.fleet";
  }
  for (const { prefix, feature } of PATH_FEATURES) {
    if (path === prefix || path.startsWith(`${prefix}/`)) {
      return feature;
    }
  }
  return null;
}

export function canAccessPath(
  role: string | null | undefined,
  pathname: string
): boolean {
  const feature = featureForPath(pathname);
  if (!feature) return true;
  return canAccess(role, feature);
}

export function homePathForRole(role: string | null | undefined): string {
  const r = normalizeAppRole(role);
  if (r === "driver") return "/driver/dashboard";
  if (r === "org_admin" || r === "super_admin") return "/admin/dashboard";
  return "/fleet/dashboard";
}

export function navLinksForRole(role: string | null | undefined) {
  const seen = new Set<string>();
  const links: Array<{ href: string; label: string; external?: boolean }> = [];
  for (const feature of featuresForRole(role)) {
    for (const link of FEATURE_LINKS[feature]) {
      if (seen.has(link.href)) continue;
      seen.add(link.href);
      links.push(link);
    }
  }
  return links;
}

export function shellMetaForRole(role: string | null | undefined): {
  eyebrow: string;
  title: string;
  accent: string;
} {
  const r = normalizeAppRole(role);
  if (r === "driver") {
    return {
      eyebrow: "Driver workspace",
      title: "My drive",
      accent: "text-emerald-300",
    };
  }
  if (r === "maintenance_tech") {
    return {
      eyebrow: "Maintenance workspace",
      title: "Vehicle health",
      accent: "text-violet-300",
    };
  }
  if (r === "org_admin" || r === "super_admin") {
    return {
      eyebrow: "Admin workspace",
      title: "Organization control",
      accent: "text-fuchsia-300",
    };
  }
  return {
    eyebrow: "Fleet workspace",
    title: "Fleet operations",
    accent: "text-sky-300",
  };
}

/** @deprecated use AppRole — coarse buckets for older call sites */
export type DashboardRole = "driver" | "fleet" | "admin";

export function normalizeDashboardRole(
  role: string | null | undefined
): DashboardRole {
  const r = normalizeAppRole(role);
  if (r === "driver") return "driver";
  if (r === "org_admin" || r === "super_admin") return "admin";
  return "fleet";
}
