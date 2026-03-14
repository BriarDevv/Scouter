/**
 * API client layer — prefers the real backend and falls back to local mocks
 * so the dashboard stays usable while the integration is being completed.
 */

import type {
  EmailThreadDetail,
  EmailThreadSummary,
  Lead,
  InboundMailStatus,
  InboundMessage,
  OutreachDraft,
  OutreachDelivery,
  OutreachLog,
  SuppressionEntry,
  PaginatedResponse,
  PipelineRunSummary,
  TaskResponse,
  TaskStatusRecord,
  DashboardStats,
  PipelineStage,
  TimeSeriesPoint,
  IndustryBreakdown,
  CityBreakdown,
  SourcePerformance,
  DraftStatus,
  InboundClassificationStatus,
  LeadStatus,
  LLMSettings,
  MailSettings,
  ReplyAssistantDraft,
  ReplyAssistantDraftReview,
  ReplyAssistantSend,
  ReplyAssistantSendStatusResponse,
  OperationalSettings,
  CredentialsStatus,
  MailCredentials,
  ConnectionTestResult,
  SetupStatus,
  NotificationItem,
  NotificationListResponse,
  NotificationCounts,
  WhatsAppCredentials,
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
  MOCK_LOGS,
} from "@/data/mock";

const USE_REAL_API = process.env.NEXT_PUBLIC_USE_REAL_API !== "false";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

async function withMockFallback<T>(loadReal: () => Promise<T>, loadMock: () => T): Promise<T> {
  if (!USE_REAL_API) {
    return loadMock();
  }
  try {
    return await loadReal();
  } catch (error) {
    console.warn("Falling back to mock data for dashboard API call", error);
    return loadMock();
  }
}

// ─── Leads ─────────────────────────────────────────────

export async function getLeads(params?: {
  page?: number;
  page_size?: number;
  status?: LeadStatus;
  min_score?: number;
}): Promise<PaginatedResponse<Lead>> {
  return withMockFallback(
    async () => {
      const query = new URLSearchParams();
      if (params?.page) query.set("page", String(params.page));
      if (params?.page_size) query.set("page_size", String(params.page_size));
      if (params?.status) query.set("status", params.status);
      if (params?.min_score !== undefined) query.set("min_score", String(params.min_score));
      const suffix = query.size ? `?${query.toString()}` : "";
      return apiFetch(`/leads${suffix}`);
    },
    () => ({
      items: MOCK_LEADS,
      total: MOCK_LEADS.length,
      page: params?.page ?? 1,
      page_size: params?.page_size ?? 50,
    })
  );
}

export async function getLeadById(id: string): Promise<Lead> {
  return withMockFallback(
    () => apiFetch(`/leads/${id}`),
    () => {
      const lead = MOCK_LEADS.find((item) => item.id === id);
      if (!lead) {
        throw new Error("Lead not found");
      }
      return lead;
    }
  );
}

export async function createLead(data: Partial<Lead>): Promise<Lead> {
  return withMockFallback(
    () => apiFetch("/leads", { method: "POST", body: JSON.stringify(data) }),
    () => ({ ...MOCK_LEADS[0], ...data, id: crypto.randomUUID() })
  );
}

export async function updateLeadStatus(id: string, status: LeadStatus): Promise<Lead> {
  return withMockFallback(
    () => apiFetch(`/leads/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
    () => {
      const lead = MOCK_LEADS.find((item) => item.id === id);
      if (!lead) {
        throw new Error("Lead not found");
      }
      return { ...lead, status };
    }
  );
}

// ─── Enrichment ────────────────────────────────────────

export async function runEnrichment(leadId: string): Promise<TaskResponse> {
  return withMockFallback(
    () => apiFetch(`/enrichment/${leadId}/async`, { method: "POST" }),
    () => ({ task_id: "mock-task-001", status: "queued" })
  );
}

// ─── Scoring ───────────────────────────────────────────

export async function runScoring(leadId: string): Promise<TaskResponse> {
  return withMockFallback(
    () => apiFetch(`/scoring/${leadId}`, { method: "POST" }),
    () => ({ task_id: "mock-task-002", status: "queued" })
  );
}

export async function runAnalysis(leadId: string): Promise<TaskResponse> {
  return withMockFallback(
    () => apiFetch(`/scoring/${leadId}/analyze`, { method: "POST" }),
    () => ({ task_id: "mock-task-003", status: "queued" })
  );
}

export async function runFullPipeline(leadId: string): Promise<TaskResponse> {
  return withMockFallback(
    () => apiFetch(`/scoring/${leadId}/pipeline`, { method: "POST" }),
    () => ({
      task_id: "mock-task-004",
      status: "queued",
      queue: "default",
      lead_id: leadId,
      pipeline_run_id: "mock-pipeline-001",
      current_step: "pipeline_dispatch",
    })
  );
}

// ─── Outreach ──────────────────────────────────────────

export async function generateDraft(leadId: string): Promise<OutreachDraft> {
  return withMockFallback(
    () => apiFetch(`/outreach/${leadId}/draft`, { method: "POST" }),
    () => ({ ...MOCK_DRAFTS[0], id: crypto.randomUUID(), lead_id: leadId })
  );
}

export async function getDrafts(params?: {
  status?: DraftStatus;
  lead_id?: string;
}): Promise<OutreachDraft[]> {
  return withMockFallback(
    async () => {
      const query = new URLSearchParams();
      if (params?.status) query.set("status", params.status);
      if (params?.lead_id) query.set("lead_id", params.lead_id);
      const suffix = query.size ? `?${query.toString()}` : "";
      return apiFetch(`/outreach/drafts${suffix}`);
    },
    () => {
      let drafts = [...MOCK_DRAFTS];
      if (params?.status) {
        drafts = drafts.filter((draft) => draft.status === params.status);
      }
      if (params?.lead_id) {
        drafts = drafts.filter((draft) => draft.lead_id === params.lead_id);
      }
      return drafts;
    }
  );
}

export async function getDraftDetail(draftId: string): Promise<OutreachDraft> {
  return apiFetch(`/outreach/drafts/${draftId}`);
}

export async function getDraftDeliveries(draftId: string): Promise<OutreachDelivery[]> {
  return apiFetch(`/outreach/drafts/${draftId}/deliveries`);
}

export async function reviewDraft(
  draftId: string,
  approved: boolean,
  feedback?: string
): Promise<OutreachDraft> {
  return withMockFallback(
    () =>
      apiFetch(`/outreach/drafts/${draftId}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: approved ? "approved" : "rejected",
          feedback,
        }),
      }),
    () => {
      const draft = MOCK_DRAFTS.find((item) => item.id === draftId);
      if (!draft) {
        throw new Error("Draft not found");
      }
      return { ...draft, status: approved ? "approved" : "rejected" };
    }
  );
}

export async function updateDraft(
  draftId: string,
  data: Partial<Pick<OutreachDraft, "subject" | "body" | "status">> & { feedback?: string }
): Promise<OutreachDraft> {
  return withMockFallback(
    () => apiFetch(`/outreach/drafts/${draftId}`, { method: "PATCH", body: JSON.stringify(data) }),
    () => {
      const draft = MOCK_DRAFTS.find((item) => item.id === draftId);
      if (!draft) {
        throw new Error("Draft not found");
      }
      return { ...draft, ...data } as OutreachDraft;
    }
  );
}

export async function getOutreachLogs(params?: {
  lead_id?: string;
  limit?: number;
}): Promise<OutreachLog[]> {
  return withMockFallback(
    async () => {
      const query = new URLSearchParams();
      if (params?.lead_id) query.set("lead_id", params.lead_id);
      if (params?.limit) query.set("limit", String(params.limit));
      const suffix = query.size ? `?${query.toString()}` : "";
      return apiFetch(`/outreach/logs${suffix}`);
    },
    () => {
      let logs = [...MOCK_LOGS];
      if (params?.lead_id) {
        logs = logs.filter((log) => log.lead_id === params.lead_id);
      }
      if (params?.limit) {
        logs = logs.slice(0, params.limit);
      }
      return logs;
    }
  );
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusRecord> {
  return withMockFallback(
    () => apiFetch(`/tasks/${taskId}/status`),
    () => ({
      task_id: taskId,
      status: "queued",
      queue: "default",
      current_step: "pipeline_dispatch",
    })
  );
}

export async function getTasks(params?: {
  status?: string;
  lead_id?: string;
  limit?: number;
}): Promise<TaskStatusRecord[]> {
  return withMockFallback(
    async () => {
      const query = new URLSearchParams();
      if (params?.status) query.set("status", params.status);
      if (params?.lead_id) query.set("lead_id", params.lead_id);
      if (params?.limit) query.set("limit", String(params.limit));
      const suffix = query.size ? `?${query.toString()}` : "";
      return apiFetch(`/tasks${suffix}`);
    },
    () => []
  );
}

export async function getPipelineRuns(params?: {
  lead_id?: string;
  status?: string;
  limit?: number;
}): Promise<PipelineRunSummary[]> {
  return withMockFallback(
    async () => {
      const query = new URLSearchParams();
      if (params?.lead_id) query.set("lead_id", params.lead_id);
      if (params?.status) query.set("status", params.status);
      if (params?.limit) query.set("limit", String(params.limit));
      const suffix = query.size ? `?${query.toString()}` : "";
      return apiFetch(`/pipelines/runs${suffix}`);
    },
    () => []
  );
}

// ─── Suppression ───────────────────────────────────────

export async function getSuppressionList(): Promise<SuppressionEntry[]> {
  return withMockFallback(
    () => apiFetch("/suppression"),
    () => MOCK_SUPPRESSION
  );
}

export async function addToSuppression(data: {
  email?: string;
  domain?: string;
  phone?: string;
  reason?: string;
}): Promise<SuppressionEntry> {
  return withMockFallback(
    () => apiFetch("/suppression", { method: "POST", body: JSON.stringify(data) }),
    () => ({
      id: crypto.randomUUID(),
      ...data,
      email: data.email ?? null,
      domain: data.domain ?? null,
      phone: data.phone ?? null,
      reason: data.reason ?? null,
      added_at: new Date().toISOString(),
    })
  );
}

export async function removeFromSuppression(id: string): Promise<void> {
  await withMockFallback(
    () => apiFetch<void>(`/suppression/${id}`, { method: "DELETE" }),
    () => undefined
  );
}

// ─── Dashboard / Performance ───────────────────────────

export async function getDashboardStats(): Promise<DashboardStats> {
  return withMockFallback(
    () => apiFetch("/dashboard/stats"),
    () => MOCK_STATS
  );
}

export async function getPipeline(): Promise<PipelineStage[]> {
  return withMockFallback(
    () => apiFetch("/dashboard/pipeline"),
    () => MOCK_PIPELINE
  );
}

export async function getTimeSeries(days?: number): Promise<TimeSeriesPoint[]> {
  return withMockFallback(
    () => apiFetch(`/dashboard/time-series${days ? `?days=${days}` : ""}`),
    () => (days ? MOCK_TIME_SERIES.slice(-days) : MOCK_TIME_SERIES)
  );
}

export async function getIndustryBreakdown(): Promise<IndustryBreakdown[]> {
  return withMockFallback(
    () => apiFetch("/performance/industry"),
    () => MOCK_INDUSTRY_BREAKDOWN
  );
}

export async function getCityBreakdown(): Promise<CityBreakdown[]> {
  return withMockFallback(
    () => apiFetch("/performance/city"),
    () => MOCK_CITY_BREAKDOWN
  );
}

export async function getSourcePerformance(): Promise<SourcePerformance[]> {
  return withMockFallback(
    () => apiFetch("/performance/source"),
    () => MOCK_SOURCE_PERFORMANCE
  );
}

// ─── Inbound Mail ─────────────────────────────────────

export async function syncInboundMail(limit?: number) {
  const suffix = limit ? `?limit=${limit}` : "";
  return apiFetch(`/mail/inbound/sync${suffix}`, { method: "POST" });
}

export async function getInboundMessages(params?: {
  lead_id?: string;
  thread_id?: string;
  classification_status?: InboundClassificationStatus;
  limit?: number;
}): Promise<InboundMessage[]> {
  const query = new URLSearchParams();
  if (params?.lead_id) query.set("lead_id", params.lead_id);
  if (params?.thread_id) query.set("thread_id", params.thread_id);
  if (params?.classification_status) query.set("classification_status", params.classification_status);
  if (params?.limit) query.set("limit", String(params.limit));
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/mail/inbound/messages${suffix}`);
}

export async function getInboundMessageById(messageId: string): Promise<InboundMessage> {
  return apiFetch(`/mail/inbound/messages/${messageId}`);
}

export async function getReplyAssistantDraft(messageId: string): Promise<ReplyAssistantDraft | null> {
  try {
    return await apiFetch(`/replies/${messageId}/draft-response`);
  } catch (error) {
    if (error instanceof Error && error.message.includes("404")) {
      return null;
    }
    throw error;
  }
}

export async function generateReplyAssistantDraft(messageId: string): Promise<ReplyAssistantDraft> {
  return apiFetch(`/replies/${messageId}/draft-response`, { method: "POST" });
}

export async function getReplyAssistantDraftReview(
  messageId: string
): Promise<ReplyAssistantDraftReview | null> {
  try {
    return await apiFetch(`/replies/${messageId}/draft-response/review`);
  } catch (error) {
    if (error instanceof Error && error.message.includes("404")) {
      return null;
    }
    throw error;
  }
}

export async function requestReplyAssistantDraftReview(messageId: string): Promise<TaskResponse> {
  return apiFetch(`/replies/${messageId}/draft-response/review`, { method: "POST" });
}

export async function updateReplyAssistantDraft(
  messageId: string,
  data: { subject?: string; body?: string; edited_by?: string }
): Promise<ReplyAssistantDraft> {
  return apiFetch(`/replies/${messageId}/draft-response`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function sendReplyAssistantDraft(messageId: string): Promise<ReplyAssistantSend> {
  return apiFetch(`/replies/${messageId}/draft-response/send`, { method: "POST" });
}

export async function getReplyAssistantSendStatus(
  messageId: string
): Promise<ReplyAssistantSendStatusResponse> {
  return apiFetch(`/replies/${messageId}/draft-response/send-status`);
}

export async function classifyInboundMessage(messageId: string): Promise<InboundMessage> {
  return apiFetch(`/mail/inbound/messages/${messageId}/classify`, { method: "POST" });
}

export async function classifyPendingInboundMessages(limit = 25): Promise<InboundMessage[]> {
  return apiFetch(`/mail/inbound/messages/classify-pending?limit=${limit}`, { method: "POST" });
}

export async function getInboundThreads(params?: {
  lead_id?: string;
  limit?: number;
}): Promise<EmailThreadSummary[]> {
  const query = new URLSearchParams();
  if (params?.lead_id) query.set("lead_id", params.lead_id);
  if (params?.limit) query.set("limit", String(params.limit));
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/mail/inbound/threads${suffix}`);
}

export async function getInboundThreadById(threadId: string): Promise<EmailThreadDetail> {
  return apiFetch(`/mail/inbound/threads/${threadId}`);
}

export async function getInboundMailStatus(): Promise<InboundMailStatus> {
  return apiFetch("/mail/inbound/status");
}

// ─── Settings ──────────────────────────────────────────

export async function getLLMSettings(): Promise<LLMSettings> {
  return apiFetch("/settings/llm");
}

export async function getMailSettings(): Promise<MailSettings> {
  return apiFetch("/settings/mail");
}

export async function getOperationalSettings(): Promise<OperationalSettings> {
  return apiFetch("/settings/operational");
}

export async function updateOperationalSettings(
  updates: Partial<OperationalSettings>
): Promise<OperationalSettings> {
  return apiFetch("/settings/operational", {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function getCredentialsStatus(): Promise<CredentialsStatus> {
  return apiFetch("/settings/credentials");
}

export async function getMailCredentials(): Promise<MailCredentials> {
  return apiFetch("/settings/mail-credentials");
}

export async function updateMailCredentials(
  updates: Partial<MailCredentials> & { smtp_password?: string; imap_password?: string }
): Promise<MailCredentials> {
  return apiFetch("/settings/mail-credentials", {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function testSmtpConnection(): Promise<ConnectionTestResult> {
  return apiFetch("/settings/test/smtp", { method: "POST" });
}

export async function testImapConnection(): Promise<ConnectionTestResult> {
  return apiFetch("/settings/test/imap", { method: "POST" });
}

export async function getSetupStatus(): Promise<SetupStatus> {
  return apiFetch("/settings/setup-status");
}

// ─── Notifications ─────────────────────────────────────

export async function getNotifications(params?: {
  page?: number;
  page_size?: number;
  category?: string;
  severity?: string;
  status?: string;
  type?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.category) searchParams.set("category", params.category);
  if (params?.severity) searchParams.set("severity", params.severity);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.type) searchParams.set("type", params.type);
  const qs = searchParams.toString();
  return apiFetch<NotificationListResponse>(`/notifications${qs ? "?" + qs : ""}`);
}

export async function getNotificationCounts() {
  return apiFetch<NotificationCounts>("/notifications/counts");
}

export async function updateNotificationStatus(id: string, status: string) {
  return apiFetch<NotificationItem>(`/notifications/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function bulkUpdateNotifications(
  action: string,
  category?: string,
  ids?: string[]
) {
  return apiFetch<{ affected: number }>("/notifications/bulk", {
    method: "POST",
    body: JSON.stringify({ action, category, ids }),
  });
}

// ─── WhatsApp ──────────────────────────────────────────

export async function getWhatsAppCredentials() {
  return apiFetch<WhatsAppCredentials>("/settings/whatsapp-credentials");
}

export async function updateWhatsAppCredentials(updates: Record<string, any>) {
  return apiFetch<WhatsAppCredentials>("/settings/whatsapp-credentials", {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function testWhatsApp() {
  return apiFetch<{ ok: boolean; error?: string; provider?: string }>(
    "/settings/test/whatsapp",
    { method: "POST" }
  );
}
