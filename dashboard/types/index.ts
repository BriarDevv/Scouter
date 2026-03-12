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
