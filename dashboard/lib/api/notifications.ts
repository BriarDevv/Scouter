import type {
  NotificationItem,
  NotificationListResponse,
  NotificationCounts,
} from "@/types";
import { apiFetch } from "./client";

// ─── Notifications ─────────────────────────────────────

export async function getNotifications(params?: {
  page?: number;
  page_size?: number;
  category?: string;
  severity?: string;
  status?: string;
  type?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.category) searchParams.set("category", params.category);
  if (params?.severity) searchParams.set("severity", params.severity);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.type) searchParams.set("type", params.type);
  const qs = searchParams.toString();
  return apiFetch<NotificationListResponse>(`/notifications${qs ? "?" + qs : ""}`);
}

export async function getNotificationCounts() {
  return apiFetch<NotificationCounts>("/notifications/counts");
}

export async function updateNotificationStatus(id: string, status: string) {
  return apiFetch<NotificationItem>(`/notifications/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function bulkUpdateNotifications(
  action: string,
  category?: string,
  ids?: string[]
) {
  return apiFetch<{ affected: number }>("/notifications/bulk", {
    method: "POST",
    body: JSON.stringify({ action, category, ids }),
  });
}
