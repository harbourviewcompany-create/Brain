import { OPERATOR_COOKIE } from "@/lib/operator-session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST() {
  const response = Response.json(
    { status: "signed_out" },
    { headers: { "cache-control": "no-store" } }
  );
  response.headers.append(
    "set-cookie",
    `${OPERATOR_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax${
      process.env.NODE_ENV === "production" ? "; Secure" : ""
    }`
  );
  return response;
}
