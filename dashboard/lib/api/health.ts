import { SYSTEM_HEALTH_URL } from "@/lib/constants";

// ─── System Health ─────────────────────────────────────────

export async function getSystemHealth(): Promise<import("@/types").SystemHealth> {
  // /health/detailed is at the app root, not under /api/v1
  const res = await fetch(SYSTEM_HEALTH_URL, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json();
}
