export type MailProvider = "gmail" | "outlook" | "zoho" | "custom";

export const SMTP_PRESETS: Record<
  MailProvider,
  { host: string; port: number; ssl: boolean; starttls: boolean } | null
> = {
  gmail: { host: "smtp.gmail.com", port: 587, ssl: false, starttls: true },
  outlook: { host: "smtp.office365.com", port: 587, ssl: false, starttls: true },
  zoho: { host: "smtp.zoho.com", port: 587, ssl: false, starttls: true },
  custom: null,
};

export const IMAP_PRESETS: Record<
  MailProvider,
  { host: string; port: number; ssl: boolean } | null
> = {
  gmail: { host: "imap.gmail.com", port: 993, ssl: true },
  outlook: { host: "outlook.office365.com", port: 993, ssl: true },
  zoho: { host: "imap.zoho.com", port: 993, ssl: true },
  custom: null,
};
