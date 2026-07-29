import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import {
  canAccessPath,
  homePathForRole,
  normalizeAppRole,
} from "@/lib/access";

const PROTECTED_PREFIXES = [
  "/driver",
  "/fleet",
  "/admin",
  "/demo",
  "/monitor",
  "/road",
  "/maintenance",
  "/safety",
  "/assistant",
  "/dashboard",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const rawRole = request.cookies.get("bmw_role")?.value || "";
  const role = rawRole ? normalizeAppRole(rawRole) : "";

  const needsAuth = PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );

  if (needsAuth && !rawRole) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", pathname);
    return NextResponse.redirect(login);
  }

  // Legacy dashboard → fleet home (if role allows) or role home
  if (pathname === "/dashboard" || pathname.startsWith("/dashboard/")) {
    if (!rawRole) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
    if (!canAccessPath(role, "/fleet/dashboard")) {
      return NextResponse.redirect(new URL(homePathForRole(role), request.url));
    }
    const url = request.nextUrl.clone();
    url.pathname = pathname.replace(/^\/dashboard/, "/fleet/dashboard");
    return NextResponse.redirect(url);
  }

  if (rawRole && !canAccessPath(role, pathname)) {
    return NextResponse.redirect(new URL(homePathForRole(role), request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard",
    "/dashboard/:path*",
    "/driver/:path*",
    "/fleet/:path*",
    "/admin/:path*",
    "/demo",
    "/demo/:path*",
    "/monitor",
    "/monitor/:path*",
    "/road",
    "/road/:path*",
    "/maintenance",
    "/maintenance/:path*",
    "/safety",
    "/safety/:path*",
    "/assistant",
    "/assistant/:path*",
    "/settings",
    "/settings/:path*",
  ],
};
