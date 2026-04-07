// ─── Mail / Inbound Types ──────────────────────────────

import type { ReplyAssistantDraft } from "./reviews";

export type InboundClassificationStatus =
  | "pending"
  | "classifying"
  | "classified"
  | "failed";

export type InboundClassificationLabel =
  | "interested"
  | "not_interested"
  | "neutral"
  | "asked_for_quote"
  | "asked_for_meeting"
  | "asked_for_more_info"
  | "wrong_contact"
  | "out_of_office"
  | "spam_or_irrelevant"
  | "needs_human_review";

export interface InboundMessage {
  id: string;
  thread_id: string | null;
  lead_id: string | null;
  draft_id: string | null;
  delivery_id: string | null;
  provider: string;
  provider_mailbox: string;
  provider_message_id: string | null;
  message_id: string | null;
  in_reply_to: string | null;
  references_raw: string | null;
  from_email: string | null;
  from_name: string | null;
  to_email: string | null;
  subject: string | null;
  body_text: string | null;
  body_snippet: string | null;
  received_at: string | null;
  raw_metadata_json: Record<string, unknown> | null;
  classification_status: InboundClassificationStatus;
  classification_label: InboundClassificationLabel | null;
  summary: string | null;
  confidence: number | null;
  next_action_suggestion: string | null;
  should_escalate_reviewer: boolean;
  classification_error: string | null;
  classification_role: string | null;
  classification_model: string | null;
  classified_at: string | null;
  reply_assistant_draft?: ReplyAssistantDraft | null;
  created_at: string;
  updated_at: string;
}

export interface EmailThreadSummary {
  id: string;
  lead_id: string | null;
  draft_id: string | null;
  delivery_id: string | null;
  provider: string;
  provider_mailbox: string;
  external_thread_id: string | null;
  thread_key: string;
  matched_via: "message_id" | "references" | "subject_fallback" | "unmatched" | string;
  match_confidence: number | null;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface EmailThreadDetail extends EmailThreadSummary {
  messages: InboundMessage[];
}

export interface InboundMailSyncRun {
  id: string;
  provider: string;
  provider_mailbox: string;
  status: "running" | "completed" | "failed" | string;
  fetched_count: number;
  new_count: number;
  deduplicated_count: number;
  matched_count: number;
  unmatched_count: number;
  error: string | null;
  started_at: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface InboundMailStatus {
  enabled: boolean;
  provider: string;
  mailbox: string;
  search_criteria: string;
  sync_limit: number;
  auto_classify_inbound: boolean;
  reviewer_labels: string[];
  last_sync: InboundMailSyncRun | null;
}
