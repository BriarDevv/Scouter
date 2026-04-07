import type {
  ReviewCorrectionSummary,
  OutcomeAnalytics,
  SignalCorrelation,
  InvestigationThread,
} from "@/types";
import type {
  AiHealthData,
  ScoringRecommendation,
  OutcomeAnalysisSummary,
  WeeklyReportData,
  OutboundConversation,
  BatchReviewProposal,
  BatchReviewSummary,
  BatchReviewDetail,
} from "@/types/reviews";
import { apiFetch } from "./client";

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

export async function getAiHealth(): Promise<AiHealthData> {
  return apiFetch<AiHealthData>("/performance/ai-health");
}

export async function getScoringRecommendations(): Promise<ScoringRecommendation[]> {
  return apiFetch<ScoringRecommendation[]>("/performance/recommendations");
}

export async function getOutcomeAnalysisSummary(): Promise<OutcomeAnalysisSummary> {
  return apiFetch<OutcomeAnalysisSummary>("/performance/analysis/summary");
}

// ─── Agent OS: Weekly Reports ──────────────────────────────────────

export async function getWeeklyReports(limit: number = 5): Promise<WeeklyReportData[]> {
  return apiFetch<WeeklyReportData[]>(`/ai-office/weekly-reports?limit=${limit}`);
}

export async function generateWeeklyReport(): Promise<WeeklyReportData> {
  return apiFetch<WeeklyReportData>("/ai-office/weekly-reports/generate", { method: "POST" });
}

// ─── Agent OS: Outbound Conversations ──────────────────────────────

export async function getOutboundConversations(limit: number = 20): Promise<OutboundConversation[]> {
  return apiFetch<OutboundConversation[]>(`/ai-office/conversations?limit=${limit}`);
}

// ─── Agent OS: Investigations ───────────────────────────────────────

export async function getInvestigation(leadId: string): Promise<InvestigationThread | null> {
  try {
    return await apiFetch<InvestigationThread>(`/performance/investigations/${leadId}`);
  } catch (err) {
    console.error("investigation_fetch_failed", err);
    return null;
  }
}

// ─── Agent OS: Batch Reviews ───────────────────────────────────────

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

// Re-export types for convenience
export type {
  AiHealthData,
  ScoringRecommendation,
  OutcomeAnalysisSummary,
  WeeklyReportData,
  OutboundConversation,
  BatchReviewProposal,
  BatchReviewSummary,
  BatchReviewDetail,
} from "@/types/reviews";
