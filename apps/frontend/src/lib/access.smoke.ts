/**
 * Lightweight mirror of backend access matrix expectations.
 * Run via: npx tsx or include in type-check (imported by access.ts consumers).
 */
import {
  canAccess,
  canAccessPath,
  homePathForRole,
  normalizeAppRole,
  type FeatureId,
} from "./access";

const EXPECT: Record<string, FeatureId[]> = {
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
};

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

export function smokeAccessMatrix() {
  assert(normalizeAppRole("viewer") === "driver", "viewer→driver");
  assert(normalizeAppRole("fleet") === "fleet_manager", "fleet cookie→fleet_manager");
  assert(homePathForRole("driver") === "/driver/dashboard", "driver home");
  assert(homePathForRole("tech") === "/fleet/dashboard" || homePathForRole("maintenance_tech") === "/fleet/dashboard", "tech home");
  assert(homePathForRole("org_admin") === "/admin/dashboard", "admin home");

  for (const [role, features] of Object.entries(EXPECT)) {
    for (const f of features) {
      assert(canAccess(role, f), `${role} should access ${f}`);
    }
  }
  assert(!canAccess("driver", "demo"), "driver cannot demo");
  assert(!canAccess("driver", "home.fleet"), "driver cannot fleet home");
  assert(!canAccessPath("driver", "/admin/dashboard"), "driver blocked from admin path");
  assert(canAccessPath("fleet_manager", "/demo"), "fleet can demo path");
  assert(!canAccessPath("maintenance_tech", "/demo"), "tech blocked from demo");
  return true;
}
