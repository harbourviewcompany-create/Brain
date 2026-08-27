import {
  OPERATOR_COOKIE,
  accessKeyMatches,
  issueSession,
  operatorSessionConfig,
  sessionCookieOptions,
} from "@/lib/operator-session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type LoginBody = { access_key?: unknown };

export async function POST(request: Request) {
  const config = operatorSessionConfig();
  if (!config) {
    return Response.json(
      {
        detail: "operator_auth_not_configured",
        fix: "Set OBSERVATORY_ACCESS_KEY and OBSERVATORY_SESSION_SECRET on the deployment, then redeploy.",
      },
      { status: 503, headers: { "cache-control": "no-store" } }
    );
  }

  let body: LoginBody;
  try {
    body = (await request.json()) as LoginBody;
  } catch {
    return Response.json(
      { detail: "invalid_request_body" },
      { status: 400, headers: { "cache-control": "no-store" } }
    );
  }

  const submitted = typeof body.access_key === "string" ? body.access_key : "";
  if (!submitted || !(await accessKeyMatches(config, submitted))) {
    return Response.json(
      { detail: "invalid_access_key" },
      { status: 401, headers: { "cache-control": "no-store" } }
    );
  }

  const session = await issueSession(config);
  const response = Response.json(
    { status: "ok", expires_in: session.maxAge },
    { headers: { "cache-control": "no-store" } }
  );
  const options = sessionCookieOptions(session.maxAge);
  response.headers.append(
    "set-cookie",
    [
      `${OPERATOR_COOKIE}=${session.value}`,
      `Path=${options.path}`,
      `Max-Age=${options.maxAge}`,
      "HttpOnly",
      `SameSite=${options.sameSite === "lax" ? "Lax" : "Strict"}`,
      options.secure ? "Secure" : "",
    ]
      .filter(Boolean)
      .join("; ")
  );
  return response;
}
