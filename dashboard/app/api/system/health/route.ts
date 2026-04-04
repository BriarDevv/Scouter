export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND_ROOT = (process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1").replace(/\/api\/v1\/?$/, "");
const SERVER_API_KEY = process.env.API_KEY || "";

export async function GET() {
  const headers = new Headers();
  if (SERVER_API_KEY) {
    headers.set("X-API-Key", SERVER_API_KEY);
  }
  const upstream = await fetch(`${BACKEND_ROOT}/health/detailed`, {
    method: "GET",
    headers,
    cache: "no-store",
  });
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: upstream.headers,
  });
}
