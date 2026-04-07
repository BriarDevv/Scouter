// ─── Dashboard / Performance Types ────────────────────

import type { LeadStatus } from "./leads";
import type { TimeSeriesPoint } from "./common";

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
  last_lead_at: string | null;
}

export interface PipelineStage {
  stage: LeadStatus;
  label: string;
  count: number;
  percentage: number;
  color: string;
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
