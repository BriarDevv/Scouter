import type {
  OutreachDraft,
  OutreachDelivery,
  OutreachLog,
  DraftStatus,
  TaskResponse,
  TaskStatusRecord,
} from "@/types";
import { apiFetch } from "./client";

// ─── Outreach ──────────────────────────────────────────

export async function generateDraft(leadId: string, channel: "email" | "whatsapp" = "email"): Promise<OutreachDraft> {
  return apiFetch(`/outreach/${leadId}/draft?channel=${channel}`, { method: "POST" });
}

export async function getDrafts(params?: {
  status?: DraftStatus;
  lead_id?: string;
}): Promise<OutreachDraft[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.lead_id) query.set("lead_id", params.lead_id);
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/outreach/drafts${suffix}`);
}

export async function getDraftDetail(draftId: string): Promise<OutreachDraft> {
  return apiFetch(`/outreach/drafts/${draftId}`);
}

export async function getDraftDeliveries(draftId: string): Promise<OutreachDelivery[]> {
  return apiFetch(`/outreach/drafts/${draftId}/deliveries`);
}

export async function sendOutreachDraft(draftId: string): Promise<OutreachDelivery> {
  return apiFetch(`/outreach/drafts/${draftId}/send`, { method: "POST" });
}

export async function reviewLeadWithIA(leadId: string): Promise<TaskResponse> {
  return apiFetch(`/reviews/leads/${leadId}/async`, { method: "POST" });
}

export async function reviewDraft(
  draftId: string,
  approved: boolean,
  feedback?: string
): Promise<OutreachDraft> {
  return apiFetch(`/outreach/drafts/${draftId}`, {
    method: "PATCH",
    body: JSON.stringify({
      status: approved ? "approved" : "rejected",
      feedback,
    }),
  });
}

export async function updateDraft(
  draftId: string,
  data: Partial<Pick<OutreachDraft, "subject" | "body" | "status">> & { feedback?: string }
): Promise<OutreachDraft> {
  return apiFetch(`/outreach/drafts/${draftId}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function getOutreachLogs(params?: {
  lead_id?: string;
  limit?: number;
}): Promise<OutreachLog[]> {
  const query = new URLSearchParams();
  if (params?.lead_id) query.set("lead_id", params.lead_id);
  if (params?.limit) query.set("limit", String(params.limit));
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/outreach/logs${suffix}`);
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusRecord> {
  return apiFetch(`/tasks/${taskId}/status`);
}

export async function getTasks(params?: {
  status?: string;
  lead_id?: string;
  limit?: number;
}): Promise<TaskStatusRecord[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.lead_id) query.set("lead_id", params.lead_id);
  if (params?.limit) query.set("limit", String(params.limit));
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/tasks${suffix}`);
}
