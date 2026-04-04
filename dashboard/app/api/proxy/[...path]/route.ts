import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND_API_BASE =
  process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
const SERVER_API_KEY = process.env.API_KEY || "";

/** Allowed API path prefixes — requests outside this list get 403. */
const ALLOWED_PREFIXES = [
  "ai-office/", "briefs/", "chat/", "crawl/",
  "dashboard/", "enrichment/", "leader/", "leads/",
  "mail/", "notifications/", "outreach/", "performance/",
  "pipelines/", "replies/", "reviews/", "scoring/",
  "settings/", "setup/", "suppression/", "tasks/",
  "telegram/", "territories/", "whatsapp/",
];

function isAllowedPath(pathname: string): boolean {
  // Block path traversal attempts
  if (pathname.includes("..") || pathname.includes("//")) return false;
  const normalized = pathname.replace(/^\/+/, "");
  // Match "leads/..." or bare "leads" (no trailing slash for root resource)
  return ALLOWED_PREFIXES.some(
    (prefix) => normalized.startsWith(prefix) || normalized === prefix.slice(0, -1),
  );
}

const HOP_BY_HOP = new Set([
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function buildHeaders(source: Headers): Headers {
  const headers = new Headers();
  source.forEach((value, key) => {
    const normalized = key.toLowerCase();
    if (HOP_BY_HOP.has(normalized)) return;
    if (normalized === "x-api-key") return;
    headers.set(key, value);
  });
  if (SERVER_API_KEY) {
    headers.set("X-API-Key", SERVER_API_KEY);
  }
  return headers;
}

async function proxyRequest(request: NextRequest, params: Promise<{ path: string[] }>) {
  const { path } = await params;
  const pathname = path.join("/");

  if (!isAllowedPath(pathname)) {
    return new Response(JSON.stringify({ detail: "Proxy: path not allowed" }), {
      status: 403,
      headers: { "Content-Type": "application/json" },
    });
  }

  const url = new URL(`${BACKEND_API_BASE.replace(/\/$/, "")}/${pathname}`);
  url.search = request.nextUrl.search;

  const init: RequestInit = {
    method: request.method,
    headers: buildHeaders(request.headers),
    cache: "no-store",
    redirect: "manual",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  const upstream = await fetch(url, init);
  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context.params);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context.params);
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context.params);
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context.params);
}

export async function OPTIONS(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context.params);
}
