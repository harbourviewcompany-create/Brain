import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import {
  OPERATOR_COOKIE,
  operatorSessionConfig,
  verifySession,
} from "@/lib/operator-session";

/**
 * Nothing reaches the Brain BFF, the cockpit pages, or the diagnostics route
 * without a valid operator session. The proxy attaches the server-side Brain
 * API key to everything it forwards, so an unauthenticated caller here is an
 * unauthenticated caller against the Brain itself.
 */

const PUBLIC_PATHS = new Set(["/login", "/api/auth/login", "/api/auth/logout"]);

function isPublic(pathname: string): boolean {
  return PUBLIC_PATHS.has(pathname);
}

function isApiPath(pathname: string): boolean {
  return pathname.startsWith("/api/");
}

function unauthorized(request: NextRequest, reason: string, status: number): NextResponse {
  const { pathname, search } = request.nextUrl;

  if (isApiPath(pathname)) {
    return NextResponse.json(
      { detail: reason },
      { status, headers: { "cache-control": "no-store" } }
    );
  }

  const login = request.nextUrl.clone();
  login.pathname = "/login";
  login.search = "";
  login.searchParams.set("reason", reason);
  if (pathname !== "/") login.searchParams.set("next", `${pathname}${search}`);
  return NextResponse.redirect(login);
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (isPublic(pathname)) return NextResponse.next();

  const config = operatorSessionConfig();
  if (!config) {
    // Fail closed. A missing access key must never read as "auth not required".
    return unauthorized(request, "operator_auth_not_configured", 503);
  }

  const cookie = request.cookies.get(OPERATOR_COOKIE)?.value;
  if (!(await verifySession(config, cookie))) {
    return unauthorized(request, "operator_session_required", 401);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Guard everything except Next.js build output and static assets. Listing
     * exclusions rather than inclusions means a route added later is protected
     * by default instead of being silently exposed.
     */
    "/((?!_next/static|_next/image|favicon.ico|robots.txt).*)",
  ],
};
