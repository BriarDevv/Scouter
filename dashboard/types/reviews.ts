// ─── Reviews / Reply Assistant Types ──────────────────

export type ReplyAssistantSendStatus = "pending" | "sending" | "sent" | "failed";

export interface ReplyAssistantSend {
  id: string;
  reply_assistant_draft_id: string;
  inbound_message_id: string;
  thread_id: string | null;
  lead_id: string | null;
  status: ReplyAssistantSendStatus;
  provider: string;
  provider_message_id: string | null;
  recipient_email: string;
  from_email_snapshot: string | null;
  reply_to_snapshot: string | null;
  subject_snapshot: string;
  body_snapshot: string;
  in_reply_to: string | null;
  references_raw: string | null;
  error: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReplyAssistantDraftReview {
  id: string;
  reply_assistant_draft_id: string;
  inbound_message_id: string;
  thread_id: string | null;
  lead_id: string | null;
  status: "pending" | "reviewed" | "failed" | string;
  summary: string | null;
  feedback: string | null;
  suggested_edits: string[] | null;
  recommended_action: string | null;
  should_use_as_is: boolean;
  should_edit: boolean;
  should_escalate: boolean;
  reviewer_role: string | null;
  reviewer_model: string | null;
  task_id: string | null;
  error: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReplyAssistantDraft {
  id: string;
  inbound_message_id: string;
  thread_id: string | null;
  lead_id: string | null;
  related_delivery_id: string | null;
  related_outbound_draft_id: string | null;
  status: string;
  subject: string;
  body: string;
  summary: string | null;
  suggested_tone: string | null;
  should_escalate_reviewer: boolean;
  generator_role: string;
  generator_model: string;
  edited_at: string | null;
  edited_by: string | null;
  review_is_stale: boolean;
  send_blocked_reason: string | null;
  latest_send: ReplyAssistantSend | null;
  review?: ReplyAssistantDraftReview | null;
  created_at: string;
  updated_at: string;
}

export interface ReplyAssistantSendStatusResponse {
  draft_id: string;
  inbound_message_id: string;
  review_is_stale: boolean;
  send_blocked_reason: string | null;
  latest_send: ReplyAssistantSend | null;
  sent: boolean;
}

export interface ReviewCorrectionSummary {
  category: string;
  count: number;
  recent_examples: string[];
}

export interface OutcomeAnalytics {
  total_won: number;
  total_lost: number;
  by_industry: { industry: string; won: number; lost: number }[];
  by_quality: { quality: string; won: number; lost: number }[];
  top_signals_won: { signal: string; count: number }[];
}

export interface SignalCorrelation {
  signal: string;
  won: number;
  lost: number;
  total: number;
  win_rate: number;
}

// ─── AI Health & Performance Types ──────────────────────

export interface AiHealthData {
  approval_rate: number;
  fallback_rate: number;
  avg_latency_ms: number | null;
  invocations_24h: number;
}

export interface ScoringRecommendation {
  type: string;
  signal?: string;
  category?: string;
  message: string;
  confidence: string;
}

export interface OutcomeAnalysisSummary {
  total_outcomes: number;
  win_rate: number;
  top_signals: { signal: string; win_rate: number }[];
  top_industries: { industry: string; won: number; lost: number }[];
  recommendations: ScoringRecommendation[];
}

// ─── Weekly Reports ──────────────────────────────────────

export interface WeeklyReportData {
  id: string;
  week_start: string;
  week_end: string;
  metrics_json: Record<string, unknown>;
  recommendations_json: unknown[];
  synthesis_text: string;
  created_at: string;
}

// ─── Outbound Conversations ──────────────────────────────

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

// ─── Batch Reviews ───────────────────────────────────────

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
