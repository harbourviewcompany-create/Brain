import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import {
  OPERATOR_COOKIE,
  operatorSessionConfig,
  verifySession,
} from "@/lib/operator-session";

/**
 * Optional operator gate in front of the Observatory UI and BFF.
 *
 * When OBSERVATORY_ACCESS_KEY and OBSERVATORY_SESSION_SECRET are both set,
 * every non-public route requires a valid signed session cookie.
 *
 * When either is missing, the deployment is intentionally open: the Brain API
 * key still never leaves the server-side BFF, and upstream Railway auth remains
 * the production boundary. Do not treat "unconfigured" as fail-closed — that
 * locked the control plane after #157 merged without Vercel secrets.
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
    // Open by default when operator secrets are not configured.
    return NextResponse.next();
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
     * When operator auth is configured, guard everything except Next.js build
     * output and static assets. Listing exclusions rather than inclusions means
     * a route added later is protected by default instead of being silently exposed.
     */
    "/((?!_next/static|_next/image|favicon.ico|robots.txt).*)",
  ],
};
