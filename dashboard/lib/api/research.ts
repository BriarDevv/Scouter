import type {
  LeadResearchReport,
  CommercialBrief,
} from "@/types";
import { apiFetch } from "./client";

// ─── Research / Dossier ─────────────────────────────────────────────

export async function getLeadResearch(leadId: string): Promise<LeadResearchReport | null> {
  try {
    return await apiFetch<LeadResearchReport>(`/leads/${leadId}/research`);
  } catch {
    return null;
  }
}

export async function runResearch(leadId: string): Promise<LeadResearchReport> {
  return apiFetch<LeadResearchReport>(`/leads/${leadId}/research`, { method: "POST" });
}

// ─── Commercial Brief ───────────────────────────────────────────────

export async function getCommercialBrief(leadId: string): Promise<CommercialBrief | null> {
  try {
    return await apiFetch<CommercialBrief>(`/briefs/leads/${leadId}`);
  } catch {
    return null;
  }
}

export async function generateBrief(leadId: string): Promise<CommercialBrief> {
  return apiFetch<CommercialBrief>(`/briefs/leads/${leadId}`, { method: "POST" });
}

export async function listBriefs(params?: { budget_tier?: string; contact_priority?: string; limit?: number }): Promise<CommercialBrief[]> {
  const qs = new URLSearchParams();
  if (params?.budget_tier) qs.set("budget_tier", params.budget_tier);
  if (params?.contact_priority) qs.set("contact_priority", params.contact_priority);
  if (params?.limit) qs.set("limit", String(params.limit));
  const q = qs.toString();
  return apiFetch<CommercialBrief[]>(`/briefs/${q ? `?${q}` : ""}`);
}
