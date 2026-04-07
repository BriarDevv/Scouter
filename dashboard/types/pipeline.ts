// ─── Pipeline Types ────────────────────────────────────

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
  scope_key?: string | null;
  progress_json?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
  error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  stop_requested_at?: string | null;
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

export interface PageVisit {
  url: string;
  title: string | null;
  status_code: number | null;
}

export interface StepContext {
  enrichment?: { signals: string[]; email_found: boolean; website_exists: boolean; instagram_exists: boolean };
  scoring?: { score: number; signal_count: number };
  analysis?: { quality: string; reasoning: string; suggested_angle: string; summary: string | null };
  scout?: { pages_visited: PageVisit[]; findings: Record<string, unknown>; loops_used: number; duration_ms: number };
  research?: { status: string; website_exists: boolean; whatsapp_detected: boolean; signals: unknown[] | null; business_description: string | null };
  brief?: { opportunity_score: number | null; budget_tier: string | null; estimated_scope: string | null; recommended_contact_method: string | null; recommended_angle: string | null; why_this_lead_matters: string | null };
  brief_review?: { approved: boolean | null; verdict_reasoning: string | null };
}

export interface BatchPipelineProgress {
  status: string;
  task_id?: string;
  total?: number;
  processed?: number;
  current_lead?: string | null;
  current_step?: string;
  errors?: number;
}
