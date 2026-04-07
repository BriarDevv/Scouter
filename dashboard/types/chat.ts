// ─── Chat Types ────────────────────────────────────────

export interface ChatConversation {
  id: string;
  channel: string;
  title: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatConversationSummary {
  id: string;
  title: string | null;
  message_count: number;
  last_message_at: string | null;
  created_at: string;
}

export interface ChatToolCall {
  id: string;
  tool_name: string;
  arguments: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  error: string | null;
  status: string;
  duration_ms: number | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string | null;
  attachments: Array<{ filename: string; content_type: string; url: string; size: number }> | null;
  tool_calls: ChatToolCall[];
  model: string | null;
  created_at: string;
}

export interface ChatConversationDetail extends ChatConversation {
  messages: ChatMessage[];
}
