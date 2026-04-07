// ─── Settings Types ────────────────────────────────────

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
  signature_is_solo: boolean;
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
  allow_reply_assistant_generation: boolean;
  use_reviewer_for_labels: string[];
  // Notifications & WhatsApp
  notifications_enabled: boolean;
  notification_score_threshold: number;
  whatsapp_alerts_enabled: boolean;
  whatsapp_min_severity: string;
  whatsapp_categories: string[];
  whatsapp_outreach_enabled: boolean;
  // Telegram
  telegram_alerts_enabled: boolean;
  // Hermes 3 agent per channel
  telegram_agent_enabled: boolean;
  whatsapp_agent_enabled: boolean;
  // Resource mode
  low_resource_mode: boolean | null;
  runtime_mode: string | null;
  pricing_matrix: string | null;
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
  kapso_api_key: boolean;
}

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

export interface SetupReadinessStep extends SetupStep {
  required: boolean;
}

export interface SetupAction {
  id: string;
  label: string;
  kind: "api" | "manual";
  description: string;
  method: string;
  endpoint: string | null;
  manual_instructions: string | null;
}

export interface SetupUpdateStatus {
  supported: boolean;
  current_branch: string | null;
  updates_available: boolean;
  dirty: boolean;
  can_autopull: boolean;
  detail: string | null;
}

export interface SetupReadiness {
  overall: "blocked" | "setup_required" | "config_required" | "ready";
  summary: string;
  target_platform: string;
  current_platform: string;
  dashboard_unlocked: boolean;
  hermes_unlocked: boolean;
  recommended_route: string;
  platform_steps: SetupReadinessStep[];
  runtime_steps: SetupReadinessStep[];
  config_steps: SetupReadinessStep[];
  wizard_steps: string[];
  actions: SetupAction[];
  updates: SetupUpdateStatus;
}

export interface SetupActionResult {
  action_id: string;
  status: "completed" | "failed" | "noop";
  summary: string;
  detail: string | null;
  stdout_tail: string | null;
  manual_instructions: string | null;
}

export interface WhatsAppCredentials {
  provider: string;
  phone_number: string | null;
  api_key_set: boolean;
  webhook_secret_set: boolean;
  webhook_url: string | null;
  last_test_at: string | null;
  last_test_ok: boolean | null;
  last_test_error: string | null;
  updated_at: string | null;
}

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
