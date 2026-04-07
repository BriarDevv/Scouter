// ─── Notification Types ────────────────────────────────

export interface NotificationItem {
  id: string;
  type: string;
  category: "business" | "system" | "security";
  severity: "info" | "warning" | "high" | "critical";
  title: string;
  message: string;
  source_kind: string | null;
  source_id: string | null;
  metadata: Record<string, unknown> | null;
  status: "unread" | "read" | "acknowledged" | "resolved";
  read_at: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  channel_state: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  total: number;
  page: number;
  page_size: number;
  unread_count: number;
}

export interface NotificationCounts {
  total_unread: number;
  business: number;
  system: number;
  security: number;
  critical: number;
  high: number;
}
