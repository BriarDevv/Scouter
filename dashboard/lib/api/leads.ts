import type {
  Lead,
  LeadName,
  LeadStatus,
  PaginatedResponse,
  TaskResponse,
  SuppressionEntry,
} from "@/types";
import { apiFetch } from "./client";
import { API_BASE_URL } from "@/lib/constants";

// ─── Leads ─────────────────────────────────────────────

export async function getLeads(params?: {
  page?: number;
  page_size?: number;
  status?: LeadStatus;
  min_score?: number;
}): Promise<PaginatedResponse<Lead>> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  if (params?.status) query.set("status", params.status);
  if (params?.min_score !== undefined) query.set("min_score", String(params.min_score));
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/leads${suffix}`);
}

export async function getLeadNames(): Promise<LeadName[]> {
  return apiFetch("/leads/names");
}

export async function getLeadById(id: string): Promise<Lead> {
  return apiFetch(`/leads/${id}`);
}

export async function createLead(data: Partial<Lead>): Promise<Lead> {
  return apiFetch("/leads", { method: "POST", body: JSON.stringify(data) });
}

export async function updateLeadStatus(id: string, status: LeadStatus): Promise<Lead> {
  return apiFetch(`/leads/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
}

// ─── Enrichment ────────────────────────────────────────

export async function runEnrichment(leadId: string): Promise<TaskResponse> {
  return apiFetch(`/enrichment/${leadId}/async`, { method: "POST" });
}

// ─── Scoring ───────────────────────────────────────────

export async function runScoring(leadId: string): Promise<TaskResponse> {
  return apiFetch(`/scoring/${leadId}`, { method: "POST" });
}

export async function runAnalysis(leadId: string): Promise<TaskResponse> {
  return apiFetch(`/scoring/${leadId}/analyze`, { method: "POST" });
}

export async function runFullPipeline(leadId: string): Promise<TaskResponse> {
  return apiFetch(`/scoring/${leadId}/pipeline`, { method: "POST" });
}

// ─── Suppression ───────────────────────────────────────

export async function getSuppressionList(): Promise<SuppressionEntry[]> {
  return apiFetch("/suppression");
}

export async function addToSuppression(data: {
  email?: string;
  domain?: string;
  phone?: string;
  reason?: string;
}): Promise<SuppressionEntry> {
  return apiFetch("/suppression", { method: "POST", body: JSON.stringify(data) });
}

export async function removeFromSuppression(id: string): Promise<void> {
  return apiFetch<void>(`/suppression/${id}`, { method: "DELETE" });
}

// ─── Export ─────────────────────────────────────────────

export function getExportUrl(format: "csv" | "json" | "xlsx", params?: { status?: string; quality?: string }): string {
  const qs = new URLSearchParams({ format });
  if (params?.status) qs.set("status", params.status);
  if (params?.quality) qs.set("quality", params.quality);
  return `${API_BASE_URL}/leads/export?${qs.toString()}`;
}

// ─── Map (individual leads) ───────────────────────────

const LEADS_WITH_COORDS_MAX_PAGES = 10;

export async function getLeadsWithCoords(signal?: AbortSignal): Promise<Lead[]> {
  const all: Lead[] = [];
  let page = 1;
  while (page <= LEADS_WITH_COORDS_MAX_PAGES) {
    if (signal?.aborted) break;
    const res = await apiFetch<PaginatedResponse<Lead>>(
      `/leads?page=${page}&page_size=200`,
      signal ? { signal } : undefined
    );
    all.push(...res.items);
    if (all.length >= res.total) break;
    page++;
  }
  return all.filter((l) =>
    l.latitude !== null && l.longitude !== null &&
    l.latitude >= -55 && l.latitude <= -21 &&
    l.longitude >= -73 && l.longitude <= -53
  );
}
