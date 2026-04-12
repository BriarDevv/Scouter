export type TabId =
  | "setup"
  | "identity"
  | "email"
  | "whatsapp"
  | "telegram"
  | "ai"
  | "notifications"
  | "data";

export type EmailSubTab =
  | "mail"
  | "credentials"
  | "signature"
  | "rules";
export type DataSubTab = "territories" | "crawlers" | "pricing";
export type WhatsAppSubTab = "alerts" | "outreach" | "agent";
export type TelegramSubTab = "bot" | "agent";

export const TABS: Array<{ id: TabId; label: string }> = [
  { id: "setup", label: "Inicio" },
  { id: "identity", label: "Identidad" },
  { id: "email", label: "Email" },
  { id: "whatsapp", label: "WhatsApp" },
  { id: "telegram", label: "Telegram" },
  { id: "ai", label: "IA" },
  { id: "notifications", label: "Notificaciones" },
  { id: "data", label: "Datos" },
];
