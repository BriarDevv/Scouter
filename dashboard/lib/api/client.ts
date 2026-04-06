/**
 * API client layer — all calls go directly to the backend API.
 */

import type {
  EmailThreadDetail,
  EmailThreadSummary,
  Lead,
  LeadName,
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
  SetupReadiness,
  SetupActionResult,
  NotificationItem,
  NotificationListResponse,
  NotificationCounts,
  WhatsAppCredentials,
  ChatConversation,
  ChatConversationSummary,
  ChatConversationDetail,
  LeadResearchReport,
  CommercialBrief,
  StepContext,
  InvestigationThread,
  ReviewCorrectionSummary,
  OutcomeAnalytics,
  SignalCorrelation,
} from "@/types";
import { API_BASE_URL, SYSTEM_HEALTH_URL } from "@/lib/constants";

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

// ─── Outreach ──────────────────────────────────────────

export async function generateDraft(leadId: string): Promise<OutreachDraft> {
  return apiFetch(`/outreach/${leadId}/draft`, { method: "POST" });

}

export async function getDrafts(params?: {
  status?: DraftStatus;
  lead_id?: string;
}): Promise<OutreachDraft[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.lead_id) query.set("lead_id", params.lead_id);
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/outreach/drafts${suffix}`);

}

export async function getDraftDetail(draftId: string): Promise<OutreachDraft> {
  return apiFetch(`/outreach/drafts/${draftId}`);
}

export async function getDraftDeliveries(draftId: string): Promise<OutreachDelivery[]> {
  return apiFetch(`/outreach/drafts/${draftId}/deliveries`);
}

export async function sendOutreachDraft(draftId: string): Promise<OutreachDelivery> {
  return apiFetch(`/outreach/drafts/${draftId}/send`, { method: "POST" });
}

export async function reviewLeadWithIA(leadId: string): Promise<TaskResponse> {
  return apiFetch(`/reviews/leads/${leadId}/async`, { method: "POST" });
}

export async function reviewDraft(
  draftId: string,
  approved: boolean,
  feedback?: string
): Promise<OutreachDraft> {
  return apiFetch(`/outreach/drafts/${draftId}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: approved ? "approved" : "rejected",
          feedback,
        }),
      });

}

export async function updateDraft(
  draftId: string,
  data: Partial<Pick<OutreachDraft, "subject" | "body" | "status">> & { feedback?: string }
): Promise<OutreachDraft> {
  return apiFetch(`/outreach/drafts/${draftId}`, { method: "PATCH", body: JSON.stringify(data) });

}

export async function getOutreachLogs(params?: {
  lead_id?: string;
  limit?: number;
}): Promise<OutreachLog[]> {
  const query = new URLSearchParams();
  if (params?.lead_id) query.set("lead_id", params.lead_id);
  if (params?.limit) query.set("limit", String(params.limit));
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/outreach/logs${suffix}`);

}

export async function getTaskStatus(taskId: string): Promise<TaskStatusRecord> {
  return apiFetch(`/tasks/${taskId}/status`);

}

export async function getTasks(params?: {
  status?: string;
  lead_id?: string;
  limit?: number;
}): Promise<TaskStatusRecord[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.lead_id) query.set("lead_id", params.lead_id);
  if (params?.limit) query.set("limit", String(params.limit));
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/tasks${suffix}`);

}

export async function getPipelineRuns(params?: {
  lead_id?: string;
  status?: string;
  limit?: number;
}): Promise<PipelineRunSummary[]> {
  const query = new URLSearchParams();
  if (params?.lead_id) query.set("lead_id", params.lead_id);
  if (params?.status) query.set("status", params.status);
  if (params?.limit) query.set("limit", String(params.limit));
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/pipelines/runs${suffix}`);

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

// ─── Dashboard / Performance ───────────────────────────

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiFetch("/dashboard/stats");

}

export async function getPipeline(): Promise<PipelineStage[]> {
  return apiFetch("/dashboard/pipeline");

}

export async function getTimeSeries(days?: number): Promise<TimeSeriesPoint[]> {
  return apiFetch(`/dashboard/time-series${days ? `?days=${days}` : ""}`);

}

export async function getIndustryBreakdown(): Promise<IndustryBreakdown[]> {
  return apiFetch("/performance/industry");

}

export async function getCityBreakdown(): Promise<CityBreakdown[]> {
  return apiFetch("/performance/city");

}

export async function getSourcePerformance(): Promise<SourcePerformance[]> {
  return apiFetch("/performance/source");

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

export async function getSetupReadiness(): Promise<SetupReadiness> {
  return apiFetch("/setup/readiness");
}

export async function runSetupAction(actionId: string): Promise<SetupActionResult> {
  return apiFetch(`/setup/actions/${actionId}`, { method: "POST" });
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

export async function updateWhatsAppCredentials(updates: Record<string, unknown>) {
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

export async function testKapsoConnection(): Promise<{ status: string; message: string }> {
  return apiFetch("/settings/test/kapso", { method: "POST" });
}

// ─── Telegram ──────────────────────────────────────────

export interface TelegramCredentials {
  bot_username: string | null;
  bot_token_set: boolean;
  chat_id: string | null;
  webhook_url: string | null;
  webhook_secret_set: boolean;
  last_test_at: string | null;
  last_test_ok: boolean | null;
  last_test_error: string | null;
  updated_at: string | null;
}

export async function getTelegramCredentials(): Promise<TelegramCredentials> {
  return apiFetch("/settings/telegram-credentials");
}

export async function updateTelegramCredentials(
  updates: { bot_username?: string | null; bot_token?: string; chat_id?: string | null }
): Promise<TelegramCredentials> {
  return apiFetch("/settings/telegram-credentials", {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function testTelegramConnection(): Promise<ConnectionTestResult> {
  return apiFetch("/settings/test/telegram", { method: "POST" });
}

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

// ─── Geo / Map ─────────────────────────────────────────

export async function getGeoSummary(): Promise<import('@/types').GeoSummaryCity[]> {
  return apiFetch('/dashboard/geo-summary');

}

// ─── Territories ───────────────────────────────────────

export async function getTerritories(): Promise<import('@/types').TerritoryWithStats[]> {
  return apiFetch('/territories');

}

export async function createTerritory(data: Partial<import('@/types').Territory>): Promise<import('@/types').Territory> {
  return apiFetch('/territories', { method: 'POST', body: JSON.stringify(data) });
}

export async function updateTerritory(id: string, data: Partial<import('@/types').Territory>): Promise<import('@/types').Territory> {
  return apiFetch(`/territories/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
}

export async function deleteTerritory(id: string): Promise<void> {
  return apiFetch(`/territories/${id}`, { method: 'DELETE' });
}

export async function getTerritoryAnalytics(): Promise<import('@/types').TerritoryWithStats[]> {
  return apiFetch('/territories/analytics');

}

// ─── Batch Pipeline ───────────────────────────────────

export interface BatchPipelineProgress {
  status: string;
  task_id?: string;
  total?: number;
  processed?: number;
  current_lead?: string | null;
  current_step?: string;
  errors?: number;
}

export async function getBatchPipelineStatus(): Promise<BatchPipelineProgress | null> {
  try {
    return await apiFetch<BatchPipelineProgress>("/pipelines/batch/status");
  } catch {
    return null;
  }
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

// ─── Chat ─────────────────────────────────────────────

export async function createConversation(): Promise<ChatConversation> {
  return apiFetch("/chat/conversations", { method: "POST" });
}

export async function listConversations(limit = 20): Promise<ChatConversationSummary[]> {
  return apiFetch(`/chat/conversations?limit=${limit}`);
}

export async function getConversation(id: string): Promise<ChatConversationDetail> {
  return apiFetch(`/chat/conversations/${id}`);
}

export async function deleteConversation(id: string): Promise<void> {
  return apiFetch<void>(`/chat/conversations/${id}`, { method: "DELETE" });
}

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

// ─── Export ─────────────────────────────────────────────────────────

export function getExportUrl(format: "csv" | "json" | "xlsx", params?: { status?: string; quality?: string }): string {
  const qs = new URLSearchParams({ format });
  if (params?.status) qs.set("status", params.status);
  if (params?.quality) qs.set("quality", params.quality);
  return `${API_BASE_URL}/leads/export?${qs.toString()}`;
}

// ─── Runtime Mode ───────────────────────────────────────────────────

export async function setRuntimeMode(mode: string): Promise<OperationalSettings> {
  return apiFetch<OperationalSettings>(`/settings/runtime-mode?mode=${mode}`, { method: "POST" });
}

// ─── Agent OS: Pipeline Context ─────────────────────────────────────

export async function getPipelineContext(pipelineRunId: string): Promise<StepContext> {
  return apiFetch<StepContext>(`/pipelines/runs/${pipelineRunId}/context`);
}

// ─── Agent OS: Investigations ───────────────────────────────────────

export async function getInvestigation(leadId: string): Promise<InvestigationThread | null> {
  try {
    return await apiFetch<InvestigationThread>(`/performance/investigations/${leadId}`);
  } catch {
    return null;
  }
}

// ─── Agent OS: Review Corrections ───────────────────────────────────

export async function getCorrectionsSummary(days: number = 30): Promise<ReviewCorrectionSummary[]> {
  return apiFetch<ReviewCorrectionSummary[]>(`/reviews/corrections/summary?days=${days}`);
}

// ─── Agent OS: Outcome Analytics ────────────────────────────────────

export async function getOutcomeAnalytics(): Promise<OutcomeAnalytics> {
  return apiFetch<OutcomeAnalytics>("/performance/outcomes");
}

export async function getSignalCorrelations(): Promise<SignalCorrelation[]> {
  return apiFetch<SignalCorrelation[]>("/performance/outcomes/signals");
}

// ─── Agent OS: AI Health & Performance ─────────────────────────────

export interface AiHealthData {
  approval_rate: number;
  fallback_rate: number;
  avg_latency_ms: number | null;
  invocations_24h: number;
}

export async function getAiHealth(): Promise<AiHealthData> {
  return apiFetch<AiHealthData>("/performance/ai-health");
}

export interface ScoringRecommendation {
  type: string;
  signal?: string;
  category?: string;
  message: string;
  confidence: string;
}

export async function getScoringRecommendations(): Promise<ScoringRecommendation[]> {
  return apiFetch<ScoringRecommendation[]>("/performance/recommendations");
}

export interface OutcomeAnalysisSummary {
  total_outcomes: number;
  win_rate: number;
  top_signals: { signal: string; win_rate: number }[];
  top_industries: { industry: string; won: number; lost: number }[];
  recommendations: ScoringRecommendation[];
}

export async function getOutcomeAnalysisSummary(): Promise<OutcomeAnalysisSummary> {
  return apiFetch<OutcomeAnalysisSummary>("/performance/analysis/summary");
}

// ─── Agent OS: Weekly Reports ──────────────────────────────────────

export interface WeeklyReportData {
  id: string;
  week_start: string;
  week_end: string;
  metrics_json: Record<string, unknown>;
  recommendations_json: unknown[];
  synthesis_text: string;
  created_at: string;
}

export async function getWeeklyReports(limit: number = 5): Promise<WeeklyReportData[]> {
  return apiFetch<WeeklyReportData[]>(`/ai-office/weekly-reports?limit=${limit}`);
}

export async function generateWeeklyReport(): Promise<WeeklyReportData> {
  return apiFetch<WeeklyReportData>("/ai-office/weekly-reports/generate", { method: "POST" });
}

// ─── Agent OS: Outbound Conversations ──────────────────────────────

export interface OutboundConversation {
  id: string;
  lead_id: string;
  lead_name?: string;
  channel: string;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export async function getOutboundConversations(limit: number = 20): Promise<OutboundConversation[]> {
  return apiFetch<OutboundConversation[]>(`/ai-office/conversations?limit=${limit}`);
}

// ─── Agent OS: Batch Reviews ───────────────────────────────────────

export interface BatchReviewProposal {
  id: string;
  category: string;
  description: string;
  impact: string;
  confidence: string;
  evidence_summary: string | null;
  status: string;
  approved_by: string | null;
  applied_at: string | null;
}

export interface BatchReviewSummary {
  id: string;
  trigger_reason: string;
  batch_size: number;
  status: string;
  reviewer_verdict: string | null;
  strategy_brief: string | null;
  proposals_count: number;
  proposals_pending: number;
  created_at: string | null;
}

export interface BatchReviewDetail extends BatchReviewSummary {
  period_start: string | null;
  period_end: string | null;
  executor_draft: string | null;
  reviewer_notes: string | null;
  metrics_json: Record<string, unknown> | null;
  proposals: BatchReviewProposal[];
}

export async function getBatchReviews(limit: number = 10): Promise<BatchReviewSummary[]> {
  return apiFetch<BatchReviewSummary[]>(`/batch-reviews?limit=${limit}`);
}

export async function getBatchReviewDetail(id: string): Promise<BatchReviewDetail> {
  return apiFetch<BatchReviewDetail>(`/batch-reviews/${id}`);
}

export async function triggerBatchReview(): Promise<{ ok: boolean; task_id: string }> {
  return apiFetch("/batch-reviews/generate", { method: "POST" });
}

export async function approveProposal(id: string): Promise<{ id: string; status: string }> {
  return apiFetch(`/batch-reviews/proposals/${id}/approve`, { method: "POST" });
}

export async function rejectProposal(id: string): Promise<{ id: string; status: string }> {
  return apiFetch(`/batch-reviews/proposals/${id}/reject`, { method: "POST" });
}

export async function applyProposal(id: string): Promise<{ id: string; status: string }> {
  return apiFetch(`/batch-reviews/proposals/${id}/apply`, { method: "POST" });
}
