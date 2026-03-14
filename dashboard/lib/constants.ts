import type {
  DraftStatus,
  InboundClassificationLabel,
  InboundClassificationStatus,
  LeadQuality,
  LeadStatus,
  SignalType,
} from "@/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const STATUS_CONFIG: Record<LeadStatus, { label: string; color: string; bg: string }> = {
  new:         { label: "Nuevo",       color: "text-slate-700",   bg: "bg-slate-100" },
  enriched:    { label: "Enriquecido", color: "text-blue-700 dark:text-blue-300",    bg: "bg-blue-50" },
  scored:      { label: "Puntuado",    color: "text-indigo-700 dark:text-indigo-300",  bg: "bg-indigo-50" },
  qualified:   { label: "Calificado",  color: "text-violet-700 dark:text-violet-300",  bg: "bg-violet-50" },
  draft_ready: { label: "Draft Listo", color: "text-purple-700 dark:text-purple-300",  bg: "bg-purple-50" },
  approved:    { label: "Aprobado",    color: "text-cyan-700 dark:text-cyan-300",    bg: "bg-cyan-50" },
  contacted:   { label: "Contactado",  color: "text-amber-700 dark:text-amber-300",   bg: "bg-amber-50" },
  opened:      { label: "Abierto",     color: "text-orange-700 dark:text-orange-300",  bg: "bg-orange-50" },
  replied:     { label: "Respondió",   color: "text-emerald-700 dark:text-emerald-300", bg: "bg-emerald-50" },
  meeting:     { label: "Reunión",     color: "text-teal-700 dark:text-teal-300",    bg: "bg-teal-50" },
  won:         { label: "Ganado",      color: "text-green-700 dark:text-green-300",   bg: "bg-green-100" },
  lost:        { label: "Perdido",     color: "text-red-700 dark:text-red-300",     bg: "bg-red-50" },
  suppressed:  { label: "Suprimido",   color: "text-gray-500 dark:text-gray-400",    bg: "bg-gray-100" },
};

export const QUALITY_CONFIG: Record<LeadQuality, { label: string; color: string; bg: string; dot: string }> = {
  high:    { label: "Alto",        color: "text-emerald-700 dark:text-emerald-300", bg: "bg-emerald-50",  dot: "bg-emerald-500" },
  medium:  { label: "Medio",       color: "text-amber-700 dark:text-amber-300",   bg: "bg-amber-50",    dot: "bg-amber-500" },
  low:     { label: "Bajo",        color: "text-red-700 dark:text-red-300",     bg: "bg-red-50",      dot: "bg-red-500" },
  unknown: { label: "Sin evaluar", color: "text-slate-500",   bg: "bg-slate-100",   dot: "bg-slate-400" },
};

export const SIGNAL_CONFIG: Record<SignalType, { label: string; emoji: string; severity: "positive" | "negative" | "neutral" }> = {
  no_website:        { label: "Sin website",       emoji: "🚫", severity: "positive" },
  instagram_only:    { label: "Solo Instagram",    emoji: "📸", severity: "positive" },
  outdated_website:  { label: "Web desactualizada",emoji: "🕸️", severity: "positive" },
  no_custom_domain:  { label: "Sin dominio propio",emoji: "🔗", severity: "positive" },
  no_visible_email:  { label: "Sin email visible", emoji: "📧", severity: "positive" },
  no_ssl:            { label: "Sin SSL",           emoji: "🔓", severity: "positive" },
  weak_seo:          { label: "SEO débil",         emoji: "📉", severity: "positive" },
  no_mobile_friendly:{ label: "No mobile-friendly",emoji: "📱", severity: "positive" },
  slow_load:         { label: "Carga lenta",       emoji: "🐌", severity: "positive" },
  has_website:       { label: "Tiene website",     emoji: "🌐", severity: "negative" },
  has_custom_domain: { label: "Dominio propio",    emoji: "✅", severity: "negative" },
};

export const DRAFT_STATUS_CONFIG: Record<DraftStatus, { label: string; color: string; bg: string }> = {
  pending_review: { label: "Pendiente",  color: "text-amber-700 dark:text-amber-300",   bg: "bg-amber-50" },
  approved:       { label: "Aprobado",   color: "text-emerald-700 dark:text-emerald-300", bg: "bg-emerald-50" },
  rejected:       { label: "Rechazado",  color: "text-red-700 dark:text-red-300",     bg: "bg-red-50" },
  sent:           { label: "Enviado",    color: "text-blue-700 dark:text-blue-300",    bg: "bg-blue-50" },
};

export const INBOUND_CLASSIFICATION_STATUS_CONFIG: Record<
  InboundClassificationStatus,
  { label: string; color: string; bg: string }
> = {
  pending: { label: "Pendiente", color: "text-amber-700 dark:text-amber-300", bg: "bg-amber-50" },
  classified: { label: "Clasificado", color: "text-emerald-700 dark:text-emerald-300", bg: "bg-emerald-50" },
  failed: { label: "Falló", color: "text-rose-700 dark:text-rose-300", bg: "bg-rose-50" },
};

export const INBOUND_REPLY_LABEL_CONFIG: Record<
  InboundClassificationLabel,
  { label: string; color: string; bg: string }
> = {
  interested: { label: "Interesado", color: "text-emerald-700 dark:text-emerald-300", bg: "bg-emerald-50" },
  not_interested: { label: "No interesado", color: "text-rose-700 dark:text-rose-300", bg: "bg-rose-50" },
  neutral: { label: "Neutral", color: "text-slate-700", bg: "bg-slate-100" },
  asked_for_quote: { label: "Pidió cotización", color: "text-cyan-700 dark:text-cyan-300", bg: "bg-cyan-50" },
  asked_for_meeting: { label: "Pidió reunión", color: "text-teal-700 dark:text-teal-300", bg: "bg-teal-50" },
  asked_for_more_info: { label: "Pidió más info", color: "text-indigo-700 dark:text-indigo-300", bg: "bg-indigo-50" },
  wrong_contact: { label: "Contacto incorrecto", color: "text-orange-700 dark:text-orange-300", bg: "bg-orange-50" },
  out_of_office: { label: "Fuera de oficina", color: "text-amber-700 dark:text-amber-300", bg: "bg-amber-50" },
  spam_or_irrelevant: { label: "Spam / irrelevante", color: "text-slate-600", bg: "bg-slate-100" },
  needs_human_review: { label: "Revisión humana", color: "text-fuchsia-700 dark:text-fuchsia-300", bg: "bg-fuchsia-50" },
};

export const INBOUND_MATCH_VIA_LABELS: Record<string, string> = {
  message_id: "Header match",
  references: "References",
  subject_fallback: "Fallback por asunto",
  unmatched: "Sin match",
};

export const POSITIVE_REPLY_LABELS: InboundClassificationLabel[] = [
  "interested",
  "asked_for_quote",
  "asked_for_meeting",
  "asked_for_more_info",
];

export const PIPELINE_STAGES: LeadStatus[] = [
  "new", "enriched", "scored", "qualified", "draft_ready",
  "approved", "contacted", "opened", "replied", "meeting", "won",
];

export const SCORE_THRESHOLDS = {
  high: 60,
  medium: 30,
};

export function getScoreLevel(score: number | null): "high" | "medium" | "low" {
  if (score === null) return "low";
  if (score >= SCORE_THRESHOLDS.high) return "high";
  if (score >= SCORE_THRESHOLDS.medium) return "medium";
  return "low";
}

export const CHART_TOOLTIP_STYLE: React.CSSProperties = {
  background: "var(--card)",
  color: "var(--card-foreground)",
  border: "1px solid var(--border)",
  borderRadius: "12px",
  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.05)",
  fontSize: 12,
};
