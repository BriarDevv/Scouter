import type {
  DashboardStats,
  PipelineStage,
  TimeSeriesPoint,
  IndustryBreakdown,
  CityBreakdown,
  SourcePerformance,
  GeoSummaryCity,
} from "@/types";
import { apiFetch } from "./client";

// ─── Dashboard / Performance ───────────────────────────

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiFetch("/dashboard/stats");
}

export async function getPipeline(): Promise<PipelineStage[]> {
  return apiFetch("/dashboard/pipeline");
}

export async function getTimeSeries(days?: number): Promise<TimeSeriesPoint[]> {
  return apiFetch(`/dashboard/time-series${days ? `?days=${days}` : ""}`);
}

export async function getIndustryBreakdown(): Promise<IndustryBreakdown[]> {
  return apiFetch("/performance/industry");
}

export async function getCityBreakdown(): Promise<CityBreakdown[]> {
  return apiFetch("/performance/city");
}

export async function getSourcePerformance(): Promise<SourcePerformance[]> {
  return apiFetch("/performance/source");
}

// ─── Geo / Map ─────────────────────────────────────────

export async function getGeoSummary(): Promise<GeoSummaryCity[]> {
  return apiFetch("/dashboard/geo-summary");
}
