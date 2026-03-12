/**
 * API client layer — prepared for real backend connection.
 * Currently returns mock data. Replace implementations with fetch calls.
 *
 * TODO (backend): endpoints marked with [MOCK] need real backend support.
 */

import type {
  Lead,
  OutreachDraft,
  SuppressionEntry,
  PaginatedResponse,
  TaskResponse,
  DashboardStats,
  PipelineStage,
  TimeSeriesPoint,
  IndustryBreakdown,
  CityBreakdown,
  SourcePerformance,
  DraftStatus,
  LeadStatus,
} from "@/types";
import { API_BASE_URL } from "@/lib/constants";
import {
  MOCK_LEADS,
  MOCK_DRAFTS,
  MOCK_SUPPRESSION,
  MOCK_STATS,
  MOCK_PIPELINE,
  MOCK_TIME_SERIES,
  MOCK_INDUSTRY_BREAKDOWN,
  MOCK_CITY_BREAKDOWN,
  MOCK_SOURCE_PERFORMANCE,
} from "@/data/mock";

// Set to true to use real API instead of mock data
const USE_REAL_API = false;

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// ─── Leads ─────────────────────────────────────────────

export async function getLeads(params?: {
  page?: number;
  page_size?: number;
  status?: LeadStatus;
  min_score?: number;
}): Promise<PaginatedResponse<Lead>> {
  if (USE_REAL_API) {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    if (params?.status) query.set("status", params.status);
    if (params?.min_score) query.set("min_score", String(params.min_score));
    return apiFetch(`/leads?${query}`);
  }
  return {
    items: MOCK_LEADS,
    total: MOCK_LEADS.length,
    page: 1,
    page_size: 50,
  };
}

export async function getLeadById(id: string): Promise<Lead> {
  if (USE_REAL_API) {
    return apiFetch(`/leads/${id}`);
  }
  const lead = MOCK_LEADS.find((l) => l.id === id);
  if (!lead) throw new Error("Lead not found");
  return lead;
}

export async function createLead(data: Partial<Lead>): Promise<Lead> {
  if (USE_REAL_API) {
    return apiFetch("/leads", { method: "POST", body: JSON.stringify(data) });
  }
  return { ...MOCK_LEADS[0], ...data, id: crypto.randomUUID() };
}

export async function updateLeadStatus(id: string, status: LeadStatus): Promise<Lead> {
  // [MOCK] Backend needs a PATCH /leads/{id}/status endpoint
  const lead = MOCK_LEADS.find((l) => l.id === id);
  if (!lead) throw new Error("Lead not found");
  return { ...lead, status };
}

// ─── Enrichment ────────────────────────────────────────

export async function runEnrichment(leadId: string): Promise<TaskResponse> {
  if (USE_REAL_API) {
    return apiFetch(`/enrichment/${leadId}/async`, { method: "POST" });
  }
  return { task_id: "mock-task-001", status: "queued" };
}

// ─── Scoring ───────────────────────────────────────────

export async function runScoring(leadId: string): Promise<TaskResponse> {
  if (USE_REAL_API) {
    return apiFetch(`/scoring/${leadId}`, { method: "POST" });
  }
  return { task_id: "mock-task-002", status: "queued" };
}

export async function runAnalysis(leadId: string): Promise<TaskResponse> {
  if (USE_REAL_API) {
    return apiFetch(`/scoring/${leadId}/analyze`, { method: "POST" });
  }
  return { task_id: "mock-task-003", status: "queued" };
}

export async function runFullPipeline(leadId: string): Promise<TaskResponse> {
  if (USE_REAL_API) {
    return apiFetch(`/scoring/${leadId}/pipeline`, { method: "POST" });
  }
  return { task_id: "mock-task-004", status: "pipeline_queued" };
}

// ─── Outreach ──────────────────────────────────────────

export async function generateDraft(leadId: string): Promise<OutreachDraft> {
  if (USE_REAL_API) {
    return apiFetch(`/outreach/${leadId}/draft`, { method: "POST" });
  }
  return MOCK_DRAFTS[0];
}

export async function getDrafts(status?: DraftStatus): Promise<OutreachDraft[]> {
  if (USE_REAL_API) {
    const query = status ? `?status=${status}` : "";
    return apiFetch(`/outreach/drafts${query}`);
  }
  return status ? MOCK_DRAFTS.filter((d) => d.status === status) : MOCK_DRAFTS;
}

export async function reviewDraft(
  draftId: string,
  approved: boolean,
  feedback?: string
): Promise<OutreachDraft> {
  if (USE_REAL_API) {
    return apiFetch(`/outreach/drafts/${draftId}/review`, {
      method: "POST",
      body: JSON.stringify({ approved, feedback }),
    });
  }
  const draft = MOCK_DRAFTS.find((d) => d.id === draftId);
  if (!draft) throw new Error("Draft not found");
  return { ...draft, status: approved ? "approved" : "rejected" };
}

// ─── Suppression ───────────────────────────────────────

export async function getSuppressionList(): Promise<SuppressionEntry[]> {
  if (USE_REAL_API) {
    return apiFetch("/suppression");
  }
  return MOCK_SUPPRESSION;
}

export async function addToSuppression(data: {
  email?: string;
  domain?: string;
  phone?: string;
  reason?: string;
}): Promise<SuppressionEntry> {
  if (USE_REAL_API) {
    return apiFetch("/suppression", { method: "POST", body: JSON.stringify(data) });
  }
  return { id: crypto.randomUUID(), ...data, email: data.email ?? null, domain: data.domain ?? null, phone: data.phone ?? null, reason: data.reason ?? null, added_at: new Date().toISOString() };
}

export async function removeFromSuppression(id: string): Promise<void> {
  if (USE_REAL_API) {
    await apiFetch(`/suppression/${id}`, { method: "DELETE" });
    return;
  }
}

// ─── Dashboard / Performance ───────────────────────────
// [MOCK] All performance endpoints need backend implementation

export async function getDashboardStats(): Promise<DashboardStats> {
  return MOCK_STATS;
}

export async function getPipeline(): Promise<PipelineStage[]> {
  return MOCK_PIPELINE;
}

export async function getTimeSeries(days?: number): Promise<TimeSeriesPoint[]> {
  const data = MOCK_TIME_SERIES;
  return days ? data.slice(-days) : data;
}

export async function getIndustryBreakdown(): Promise<IndustryBreakdown[]> {
  return MOCK_INDUSTRY_BREAKDOWN;
}

export async function getCityBreakdown(): Promise<CityBreakdown[]> {
  return MOCK_CITY_BREAKDOWN;
}

export async function getSourcePerformance(): Promise<SourcePerformance[]> {
  return MOCK_SOURCE_PERFORMANCE;
}
