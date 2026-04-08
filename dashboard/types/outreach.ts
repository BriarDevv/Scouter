// ─── Outreach Types ────────────────────────────────────

import type { Lead } from "./leads";

export type DraftStatus = "pending_review" | "approved" | "rejected" | "sent";

export type LogAction =
  | "generated"
  | "reviewed"
  | "approved"
  | "rejected"
  | "sent"
  | "opened"
  | "replied"
  | "meeting"
  | "won"
  | "lost";

export interface OutreachDraft {
  id: string;
  lead_id: string;
  lead?: Lead | null;
  subject: string;
  body: string;
  channel?: string; // "email" | "whatsapp"
  status: DraftStatus;
  generation_metadata_json?: Record<string, unknown> | null;
  generated_at: string;
  reviewed_at: string | null;
  sent_at: string | null;
}

export interface OutreachDelivery {
  id: string;
  lead_id: string;
  draft_id: string;
  provider: string;
  provider_message_id: string | null;
  recipient_email: string;
  subject_snapshot: string;
  status: "sending" | "sent" | "failed";
  error: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OutreachLog {
  id: string;
  lead_id: string;
  draft_id: string | null;
  action: LogAction;
  actor: string;
  detail: string | null;
  created_at: string;
  business_name: string | null;
}
