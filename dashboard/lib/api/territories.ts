import { apiFetch } from "./client";

// ─── Territories ───────────────────────────────────────

export async function getTerritories(): Promise<import("@/types").TerritoryWithStats[]> {
  return apiFetch("/territories");
}

export async function createTerritory(data: Partial<import("@/types").Territory>): Promise<import("@/types").Territory> {
  return apiFetch("/territories", { method: "POST", body: JSON.stringify(data) });
}

export async function updateTerritory(id: string, data: Partial<import("@/types").Territory>): Promise<import("@/types").Territory> {
  return apiFetch(`/territories/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteTerritory(id: string): Promise<void> {
  return apiFetch(`/territories/${id}`, { method: "DELETE" });
}

export async function getTerritoryAnalytics(): Promise<import("@/types").TerritoryWithStats[]> {
  return apiFetch("/territories/analytics");
}
