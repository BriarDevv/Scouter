import type {
  InboundMessage,
  InboundClassificationStatus,
  EmailThreadSummary,
  EmailThreadDetail,
  InboundMailStatus,
  ReplyAssistantDraft,
  ReplyAssistantDraftReview,
  ReplyAssistantSend,
  ReplyAssistantSendStatusResponse,
  TaskResponse,
} from "@/types";
import { apiFetch } from "./client";

// ─── Inbound Mail ─────────────────────────────────────

export async function syncInboundMail(limit?: number) {
  const suffix = limit ? `?limit=${limit}` : "";
  return apiFetch(`/mail/inbound/sync${suffix}`, { method: "POST" });
}

export async function getInboundMessages(params?: {
  lead_id?: string;
  thread_id?: string;
  classification_status?: InboundClassificationStatus;
  limit?: number;
}): Promise<InboundMessage[]> {
  const query = new URLSearchParams();
  if (params?.lead_id) query.set("lead_id", params.lead_id);
  if (params?.thread_id) query.set("thread_id", params.thread_id);
  if (params?.classification_status) query.set("classification_status", params.classification_status);
  if (params?.limit) query.set("limit", String(params.limit));
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/mail/inbound/messages${suffix}`);
}

export async function getInboundMessageById(messageId: string): Promise<InboundMessage> {
  return apiFetch(`/mail/inbound/messages/${messageId}`);
}

export async function getReplyAssistantDraft(messageId: string): Promise<ReplyAssistantDraft | null> {
  try {
    return await apiFetch(`/replies/${messageId}/draft-response`);
  } catch (error) {
    if (error instanceof Error && error.message.includes("404")) {
      return null;
    }
    throw error;
  }
}

export async function generateReplyAssistantDraft(messageId: string): Promise<ReplyAssistantDraft> {
  return apiFetch(`/replies/${messageId}/draft-response`, { method: "POST" });
}

export async function getReplyAssistantDraftReview(
  messageId: string
): Promise<ReplyAssistantDraftReview | null> {
  try {
    return await apiFetch(`/replies/${messageId}/draft-response/review`);
  } catch (error) {
    if (error instanceof Error && error.message.includes("404")) {
      return null;
    }
    throw error;
  }
}

export async function requestReplyAssistantDraftReview(messageId: string): Promise<TaskResponse> {
  return apiFetch(`/replies/${messageId}/draft-response/review`, { method: "POST" });
}

export async function updateReplyAssistantDraft(
  messageId: string,
  data: { subject?: string; body?: string; edited_by?: string }
): Promise<ReplyAssistantDraft> {
  return apiFetch(`/replies/${messageId}/draft-response`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function sendReplyAssistantDraft(messageId: string): Promise<ReplyAssistantSend> {
  return apiFetch(`/replies/${messageId}/draft-response/send`, { method: "POST" });
}

export async function getReplyAssistantSendStatus(
  messageId: string
): Promise<ReplyAssistantSendStatusResponse> {
  return apiFetch(`/replies/${messageId}/draft-response/send-status`);
}

export async function classifyInboundMessage(messageId: string): Promise<InboundMessage> {
  return apiFetch(`/mail/inbound/messages/${messageId}/classify`, { method: "POST" });
}

export async function classifyPendingInboundMessages(limit = 25): Promise<InboundMessage[]> {
  return apiFetch(`/mail/inbound/messages/classify-pending?limit=${limit}`, { method: "POST" });
}

export async function getInboundThreads(params?: {
  lead_id?: string;
  limit?: number;
}): Promise<EmailThreadSummary[]> {
  const query = new URLSearchParams();
  if (params?.lead_id) query.set("lead_id", params.lead_id);
  if (params?.limit) query.set("limit", String(params.limit));
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/mail/inbound/threads${suffix}`);
}

export async function getInboundThreadById(threadId: string): Promise<EmailThreadDetail> {
  return apiFetch(`/mail/inbound/threads/${threadId}`);
}

export async function getInboundMailStatus(): Promise<InboundMailStatus> {
  return apiFetch("/mail/inbound/status");
}
