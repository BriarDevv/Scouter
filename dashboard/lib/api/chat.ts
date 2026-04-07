import type {
  ChatConversation,
  ChatConversationSummary,
  ChatConversationDetail,
} from "@/types";
import { apiFetch } from "./client";

// ─── Chat ─────────────────────────────────────────────

export async function createConversation(): Promise<ChatConversation> {
  return apiFetch("/chat/conversations", { method: "POST" });
}

export async function listConversations(limit = 20): Promise<ChatConversationSummary[]> {
  return apiFetch(`/chat/conversations?limit=${limit}`);
}

export async function getConversation(id: string): Promise<ChatConversationDetail> {
  return apiFetch(`/chat/conversations/${id}`);
}

export async function deleteConversation(id: string): Promise<void> {
  return apiFetch<void>(`/chat/conversations/${id}`, { method: "DELETE" });
}
