// ─── Common / Shared Types ─────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface TimeSeriesPoint {
  date: string;
  leads: number;
  outreach: number;
  replies: number;
  conversions: number;
}

export interface HealthComponent {
  name: string;
  status: "ok" | "error" | "degraded";
  latency_ms: number | null;
  error: string | null;
}

export interface SystemHealth {
  status: "healthy" | "degraded" | "unhealthy";
  components: HealthComponent[];
  checked_at: string;
}

export interface GeoSummaryCity {
  city: string;
  count: number;
  avg_score: number;
  qualified_count: number;
  lat: number;
  lng: number;
}

export interface Territory {
  id: string;
  name: string;
  description: string | null;
  color: string;
  cities: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TerritoryWithStats extends Territory {
  lead_count: number;
  avg_score: number;
  qualified_count: number;
  conversion_rate: number;
}

export type RuntimeMode = "safe" | "assisted" | "auto";
