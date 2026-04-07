import type {
  LLMSettings,
  MailSettings,
  OperationalSettings,
  CredentialsStatus,
  MailCredentials,
  ConnectionTestResult,
  SetupStatus,
  SetupReadiness,
  SetupActionResult,
  WhatsAppCredentials,
} from "@/types";
import type { TelegramCredentials } from "@/types/settings";
import { apiFetch } from "./client";

// ─── Settings ──────────────────────────────────────────

export async function getLLMSettings(): Promise<LLMSettings> {
  return apiFetch("/settings/llm");
}

export async function getMailSettings(): Promise<MailSettings> {
  return apiFetch("/settings/mail");
}

export async function getOperationalSettings(): Promise<OperationalSettings> {
  return apiFetch("/settings/operational");
}

export async function updateOperationalSettings(
  updates: Partial<OperationalSettings>
): Promise<OperationalSettings> {
  return apiFetch("/settings/operational", {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function getCredentialsStatus(): Promise<CredentialsStatus> {
  return apiFetch("/settings/credentials");
}

export async function getMailCredentials(): Promise<MailCredentials> {
  return apiFetch("/settings/mail-credentials");
}

export async function updateMailCredentials(
  updates: Partial<MailCredentials> & { smtp_password?: string; imap_password?: string }
): Promise<MailCredentials> {
  return apiFetch("/settings/mail-credentials", {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function testSmtpConnection(): Promise<ConnectionTestResult> {
  return apiFetch("/settings/test/smtp", { method: "POST" });
}

export async function testImapConnection(): Promise<ConnectionTestResult> {
  return apiFetch("/settings/test/imap", { method: "POST" });
}

export async function getSetupStatus(): Promise<SetupStatus> {
  return apiFetch("/settings/setup-status");
}

export async function getSetupReadiness(): Promise<SetupReadiness> {
  return apiFetch("/setup/readiness");
}

export async function runSetupAction(actionId: string): Promise<SetupActionResult> {
  return apiFetch(`/setup/actions/${actionId}`, { method: "POST" });
}

// ─── WhatsApp ──────────────────────────────────────────

export async function getWhatsAppCredentials() {
  return apiFetch<WhatsAppCredentials>("/settings/whatsapp-credentials");
}

export async function updateWhatsAppCredentials(updates: Record<string, unknown>) {
  return apiFetch<WhatsAppCredentials>("/settings/whatsapp-credentials", {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function testWhatsApp() {
  return apiFetch<{ ok: boolean; error?: string; provider?: string }>(
    "/settings/test/whatsapp",
    { method: "POST" }
  );
}

export async function testKapsoConnection(): Promise<{ status: string; message: string }> {
  return apiFetch("/settings/test/kapso", { method: "POST" });
}

// ─── Telegram ──────────────────────────────────────────

export async function getTelegramCredentials(): Promise<TelegramCredentials> {
  return apiFetch("/settings/telegram-credentials");
}

export async function updateTelegramCredentials(
  updates: { bot_username?: string | null; bot_token?: string; chat_id?: string | null }
): Promise<TelegramCredentials> {
  return apiFetch("/settings/telegram-credentials", {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function testTelegramConnection(): Promise<ConnectionTestResult> {
  return apiFetch("/settings/test/telegram", { method: "POST" });
}

// ─── Runtime Mode ───────────────────────────────────────────────────

export async function setRuntimeMode(mode: string): Promise<OperationalSettings> {
  return apiFetch<OperationalSettings>(`/settings/runtime-mode?mode=${mode}`, { method: "POST" });
}

// Re-export types for backward compatibility
export type { TelegramCredentials } from "@/types/settings";
