import { proxyToBrain } from "@/lib/brain-upstream";

export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ path: string[] }> };

async function handle(request: Request, context: Ctx) {
  const { path } = await context.params;
  const segments = Array.isArray(path) ? path : [path];
  const url = new URL(request.url);
  const body =
    request.method === "GET" || request.method === "HEAD"
      ? null
      : await request.text();

  return proxyToBrain(segments, {
    method: request.method,
    headers: request.headers,
    body,
    search: url.search,
  });
}

export async function GET(request: Request, context: Ctx) {
  return handle(request, context);
}

export async function POST(request: Request, context: Ctx) {
  return handle(request, context);
}

export async function PUT(request: Request, context: Ctx) {
  return handle(request, context);
}

export async function PATCH(request: Request, context: Ctx) {
  return handle(request, context);
}

export async function DELETE(request: Request, context: Ctx) {
  return handle(request, context);
}

export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: {
      "access-control-allow-methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
      "access-control-allow-headers": "content-type",
    },
  });
}
