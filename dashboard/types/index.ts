// ─── Enums ─────────────────────────────────────────────

export type LeadStatus =
  | "new"
  | "enriched"
  | "scored"
  | "qualified"
  | "draft_ready"
  | "approved"
  | "contacted"
  | "opened"
  | "replied"
  | "meeting"
  | "won"
  | "lost"
  | "suppressed";

export type SignalType =
  | "no_website"
  | "instagram_only"
  | "outdated_website"
  | "no_custom_domain"
  | "no_visible_email"
  | "no_ssl"
  | "weak_seo"
  | "no_mobile_friendly"
  | "slow_load"
  | "has_website"
  | "has_custom_domain";

export type DraftStatus = "pending_review" | "approved" | "rejected" | "sent";

export type LeadQuality = "high" | "medium" | "low" | "unknown";

export type InboundClassificationStatus = "pending" | "classified" | "failed";

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

export type LogAction =
  | "generated"
  | "reviewed"
  | "approved"
  | "rejected"
  | "sent"
  | "opened"
  | "replied"
  | "meeting"
  | "won"
  | "lost";

// ─── Models ────────────────────────────────────────────

export interface Lead {
  id: string;
  business_name: string;
  industry: string | null;
  city: string | null;
  zone: string | null;
  website_url: string | null;
  instagram_url: string | null;
  email: string | null;
  phone: string | null;
  source_id: string | null;
  status: LeadStatus;
  score: number | null;
  quality: LeadQuality;
  llm_summary: string | null;
  llm_quality_assessment: string | null;
  llm_suggested_angle: string | null;
  dedup_hash: string | null;
  created_at: string;
  updated_at: string;
  enriched_at: string | null;
  scored_at: string | null;
  signals?: LeadSignal[];
  source?: LeadSource | null;
  owner?: string | null;
  notes?: string | null;
}

export interface LeadSignal {
  id: string;
  lead_id: string;
  signal_type: SignalType;
  detail: string | null;
  detected_at: string;
}

export interface LeadSource {
  id: string;
  name: string;
  source_type: "manual" | "crawler" | "import";
  url: string | null;
  description: string | null;
  created_at: string;
}

export interface OutreachDraft {
  id: string;
  lead_id: string;
  lead?: Lead | null;
  subject: string;
  body: string;
  status: DraftStatus;
  generated_at: string;
  reviewed_at: string | null;
  sent_at: string | null;
}

export interface OutreachDelivery {
  id: string;
  lead_id: string;
  draft_id: string;
  provider: string;
  provider_message_id: string | null;
  recipient_email: string;
  subject_snapshot: string;
  status: "sending" | "sent" | "failed";
  error: string | null;
  sent_at: string | null;
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
  status: "generated" | string;
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

export interface ReplyAssistantSendStatusResponse {
  draft_id: string;
  inbound_message_id: string;
  review_is_stale: boolean;
  send_blocked_reason: string | null;
  latest_send: ReplyAssistantSend | null;
  sent: boolean;
}

export interface OutreachLog {
  id: string;
  lead_id: string;
  draft_id: string | null;
  action: LogAction;
  actor: string;
  detail: string | null;
  created_at: string;
}

export interface SuppressionEntry {
  id: string;
  email: string | null;
  domain: string | null;
  phone: string | null;
  reason: string | null;
  business_name?: string | null;
  added_at: string;
}

// ─── API Responses ─────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaskResponse {
  task_id: string;
  status: string;
  queue?: string | null;
  lead_id?: string | null;
  pipeline_run_id?: string | null;
  current_step?: string | null;
}

export interface TaskStatusRecord extends TaskResponse {
  correlation_id?: string | null;
  result?: Record<string, unknown> | null;
  error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface PipelineRunSummary {
  id: string;
  lead_id: string;
  correlation_id: string;
  root_task_id: string | null;
  status: string;
  current_step: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
}

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

// ─── Dashboard / Performance ───────────────────────────

export interface DashboardStats {
  total_leads: number;
  new_today: number;
  qualified: number;
  approved: number;
  contacted: number;
  replied: number;
  meetings: number;
  won: number;
  lost: number;
  suppressed: number;
  avg_score: number;
  conversion_rate: number;
  open_rate: number;
  reply_rate: number;
  positive_reply_rate: number;
  meeting_rate: number;
  pipeline_velocity: number;
}

export interface PipelineStage {
  stage: LeadStatus;
  label: string;
  count: number;
  percentage: number;
  color: string;
}

export interface TimeSeriesPoint {
  date: string;
  leads: number;
  outreach: number;
  replies: number;
  conversions: number;
}

export interface IndustryBreakdown {
  industry: string;
  count: number;
  avg_score: number;
  conversion_rate: number;
}

export interface CityBreakdown {
  city: string;
  count: number;
  avg_score: number;
  reply_rate: number;
}

export interface SourcePerformance {
  source: string;
  leads: number;
  avg_score: number;
  reply_rate: number;
  conversion_rate: number;
}

export interface PerformanceMetrics {
  stats: DashboardStats;
  pipeline: PipelineStage[];
  time_series: TimeSeriesPoint[];
  by_industry: IndustryBreakdown[];
  by_city: CityBreakdown[];
  by_source: SourcePerformance[];
  avg_time_to_contact: number;
  avg_time_to_reply: number;
  avg_time_to_meeting: number;
  avg_time_to_close: number;
}

// ─── Settings ──────────────────────────────────────────

export interface LLMRoleDefaults {
  leader: string;
  executor: string;
  reviewer: string | null;
}

export interface LLMSettings {
  provider: string;
  base_url: string;
  read_only: boolean;
  editable: boolean;
  leader_model: string;
  executor_model: string;
  reviewer_model: string | null;
  supported_models: string[];
  default_role_models: LLMRoleDefaults;
  legacy_executor_fallback_model: string;
  legacy_executor_fallback_active: boolean;
  timeout_seconds: number;
  max_retries: number;
}

export interface MailSyncCounts {
  fetched: number;
  new: number;
  deduplicated: number;
  matched: number;
  unmatched: number;
}

export interface MailLastSync {
  status: string;
  at: string | null;
  counts: MailSyncCounts;
  error: string | null;
}

export interface OutboundMailSettings {
  enabled: boolean;
  provider: string;
  configured: boolean;
  ready: boolean;
  from_email: string | null;
  from_name: string;
  reply_to: string | null;
  send_timeout_seconds: number;
  require_approved_drafts: boolean;
  missing_requirements: string[];
}

export interface InboundMailSettings {
  enabled: boolean;
  provider: string;
  configured: boolean;
  ready: boolean;
  account: string | null;
  mailbox: string;
  sync_limit: number;
  timeout_seconds: number;
  search_criteria: string;
  auto_classify_inbound: boolean;
  use_reviewer_for_labels: string[];
  last_sync: MailLastSync | null;
  missing_requirements: string[];
}

export interface MailHealthSettings {
  configured: boolean;
  enabled: boolean;
  outbound_ready: boolean;
  inbound_ready: boolean;
  last_sync_status: string | null;
  last_sync_at: string | null;
}

export interface MailSettings {
  read_only: boolean;
  editable: boolean;
  outbound: OutboundMailSettings;
  inbound: InboundMailSettings;
  health: MailHealthSettings;
}

// ─── Operational Settings ──────────────────────────────

export interface OperationalSettings {
  id: number;
  // Brand / Signature
  brand_name: string | null;
  signature_name: string | null;
  signature_role: string | null;
  signature_company: string | null;
  portfolio_url: string | null;
  website_url: string | null;
  calendar_url: string | null;
  signature_cta: string | null;
  signature_include_portfolio: boolean;
  default_outreach_tone: string;
  default_reply_tone: string;
  default_closing_line: string | null;
  // Mail outbound
  mail_enabled: boolean | null;
  mail_from_email: string | null;
  mail_from_name: string | null;
  mail_reply_to: string | null;
  mail_send_timeout_seconds: number | null;
  require_approved_drafts: boolean;
  // Mail inbound
  mail_inbound_sync_enabled: boolean | null;
  mail_inbound_mailbox: string | null;
  mail_inbound_sync_limit: number | null;
  mail_inbound_timeout_seconds: number | null;
  mail_inbound_search_criteria: string | null;
  // Rules
  auto_classify_inbound: boolean;
  reply_assistant_enabled: boolean;
  reviewer_enabled: boolean;
  reviewer_labels: string[];
  reviewer_confidence_threshold: number;
  prioritize_quote_replies: boolean;
  prioritize_meeting_replies: boolean;
  allow_openclaw_briefs: boolean;
  allow_reply_assistant_generation: boolean;
  use_reviewer_for_labels: string[];
  updated_at: string | null;
}

export interface CredentialStatusItem {
  key: string;
  label: string;
  set: boolean;
  required: boolean;
}

export interface CredentialsStatus {
  smtp: CredentialStatusItem[];
  imap: CredentialStatusItem[];
  all_smtp_ready: boolean;
  all_imap_ready: boolean;
}

// ─── Mail Credentials ──────────────────────────────────────────────

export interface MailCredentials {
  smtp_host: string | null;
  smtp_port: number;
  smtp_username: string | null;
  smtp_password_set: boolean;
  smtp_ssl: boolean;
  smtp_starttls: boolean;
  imap_host: string | null;
  imap_port: number;
  imap_username: string | null;
  imap_password_set: boolean;
  imap_ssl: boolean;
  smtp_last_test_at: string | null;
  smtp_last_test_ok: boolean | null;
  smtp_last_test_error: string | null;
  imap_last_test_at: string | null;
  imap_last_test_ok: boolean | null;
  imap_last_test_error: string | null;
  updated_at: string | null;
}

export interface ConnectionTestResult {
  ok: boolean;
  error: string | null;
  sample_count: number | null;
}

export interface SetupStep {
  id: string;
  label: string;
  status: "complete" | "incomplete" | "warning" | "pending";
  detail: string | null;
  action: string | null;
}

export interface SetupStatus {
  steps: SetupStep[];
  overall: "ready" | "incomplete" | "warning";
  ready_to_send: boolean;
  ready_to_receive: boolean;
}
