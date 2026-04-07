// ─── Research / Dossier Types ──────────────────────────

import type { PageVisit } from "./pipeline";

export type ConfidenceLevel = "confirmed" | "probable" | "unknown" | "mismatch";
export type ResearchStatus = "pending" | "running" | "completed" | "failed";

export interface LeadResearchReport {
  id: string;
  lead_id: string;
  status: ResearchStatus;
  website_exists: boolean | null;
  website_url_verified: string | null;
  website_confidence: ConfidenceLevel | null;
  instagram_exists: boolean | null;
  instagram_url_verified: string | null;
  instagram_confidence: ConfidenceLevel | null;
  whatsapp_detected: boolean | null;
  whatsapp_confidence: ConfidenceLevel | null;
  screenshots_json: Array<{ url: string; path: string; captured_at: string }> | null;
  detected_signals_json: Array<{ type: string; detail: string; confidence?: number }> | null;
  html_metadata_json: Record<string, unknown> | null;
  business_description: string | null;
  researcher_model: string | null;
  research_duration_ms: number | null;
  error: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export type BudgetTier = "low" | "medium" | "high" | "premium";
export type EstimatedScope = "landing" | "institutional_web" | "catalog" | "ecommerce" | "redesign" | "automation" | "branding_web";
export type ContactMethod = "whatsapp" | "email" | "call" | "demo_first" | "manual_review";
export type CallDecision = "yes" | "no" | "maybe";
export type ContactPriority = "immediate" | "high" | "normal" | "low";
export type BriefStatus = "pending" | "generated" | "reviewed" | "failed";

export interface CommercialBrief {
  id: string;
  lead_id: string;
  status: BriefStatus;
  opportunity_score: number | null;
  budget_tier: BudgetTier | null;
  estimated_budget_min: number | null;
  estimated_budget_max: number | null;
  estimated_scope: EstimatedScope | null;
  recommended_contact_method: ContactMethod | null;
  should_call: CallDecision | null;
  call_reason: string | null;
  why_this_lead_matters: string | null;
  main_business_signals: string[] | null;
  main_digital_gaps: string[] | null;
  recommended_angle: string | null;
  demo_recommended: boolean | null;
  contact_priority: ContactPriority | null;
  generator_model: string | null;
  reviewer_model: string | null;
  reviewed_at: string | null;
  error: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ToolCallRecord {
  name: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
  duration_ms: number;
  timestamp: number;
}

export interface InvestigationThread {
  id: string;
  lead_id: string;
  agent_model: string;
  tool_calls: ToolCallRecord[];
  pages_visited: PageVisit[];
  findings: Record<string, unknown>;
  loops_used: number;
  duration_ms: number;
  error: string | null;
  created_at: string | null;
}
