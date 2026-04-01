export type TabId =
  | "setup"
  | "brand"
  | "mail_out"
  | "mail_in"
  | "rules"
  | "credentials"
  | "notifications"
  | "whatsapp"
  | "telegram"
  | "territories"
  | "crawlers";

export const TABS: Array<{ id: TabId; label: string }> = [
  { id: "setup", label: "Inicio" },
  { id: "brand", label: "Marca / Firma" },
  { id: "mail_out", label: "Mail de salida" },
  { id: "mail_in", label: "Bandeja de entrada" },
  { id: "rules", label: "Reglas" },
  { id: "credentials", label: "Credenciales" },
  { id: "notifications", label: "Notificaciones" },
  { id: "whatsapp", label: "WhatsApp" },
  { id: "telegram", label: "Telegram" },
  { id: "territories", label: "Territorios" },
  { id: "crawlers", label: "Crawlers" },
];
