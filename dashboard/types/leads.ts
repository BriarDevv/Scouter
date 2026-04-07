// ─── Lead Types ────────────────────────────────────────

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
  | "has_custom_domain"
  | "website_error";

export type LeadQuality = "high" | "medium" | "low" | "unknown";

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
  address: string | null;
  google_maps_url: string | null;
  rating: number | null;
  review_count: number | null;
  business_status: string | null;
  opening_hours: string | null;
  latitude: number | null;
  longitude: number | null;
  dedup_hash: string | null;
  created_at: string;
  owner?: string | null;
  notes?: string | null;
  updated_at: string;
  enriched_at: string | null;
  scored_at: string | null;
  signals?: LeadSignal[];
  source?: LeadSource | null;
}

export interface LeadName {
  id: string;
  business_name: string;
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
