/**
 * API client layer — all calls go directly to the backend API.
 */

import { API_BASE_URL } from "@/lib/constants";

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const method = options?.method?.toUpperCase() || "GET";
  const maxRetries = method === "GET" ? 2 : 0;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const res = await fetch(`${API_BASE_URL}${path}`, { headers, ...options });
    if (res.status >= 500 && attempt < maxRetries) {
      await new Promise((r) => setTimeout(r, 1000 * 2 ** attempt));
      continue;
    }
    if (!res.ok) {
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    if (res.status === 204) {
      return undefined as unknown as T;
    }
    return res.json();
  }
  throw new Error("API error: max retries exceeded");
}

// ─── Domain module re-exports ───────────────────────────────────────
// These re-exports preserve backward compatibility for all existing
// imports of the form: import { X } from "@/lib/api/client"

export * from "./leads";
export * from "./outreach";
export * from "./pipeline";
export * from "./settings";
export * from "./dashboard";
export * from "./mail";
export * from "./notifications";
export * from "./chat";
export * from "./research";
export * from "./reviews";
export * from "./health";
export * from "./territories";
