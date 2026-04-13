import {
  Bell,
  Brain,
  Inbox,
  MessageCircle,
  Send,
  ShieldCheck,
  Sparkles,
  Wand2,
  Zap,
} from "lucide-react";
import type { FeatureToggle } from "@/components/dashboard/feature-toggle-list";

export const IA_FEATURES: FeatureToggle[] = [
  { key: "reply_assistant_enabled", label: "Reply Assistant", hint: "Borradores de respuesta automaticos", icon: Wand2, category: "ia" },
  { key: "reviewer_enabled", label: "Reviewer IA", hint: "Revision con modelo de 27B", icon: ShieldCheck, category: "ia" },
  { key: "auto_classify_inbound", label: "Auto-clasificar inbound", hint: "Clasifica replies automaticamente", icon: Brain, category: "ia" },
  { key: "whatsapp_agent_enabled", label: "Mote WhatsApp", hint: "Mote responde por WhatsApp", icon: Sparkles, category: "ia" },
  { key: "telegram_agent_enabled", label: "Mote Telegram", hint: "Mote responde por Telegram", icon: Sparkles, category: "ia" },
  { key: "low_resource_mode", label: "Low Resources", hint: "Modelos livianos, menos VRAM", icon: Zap, category: "ia" },
];

export const CHANNEL_FEATURES: FeatureToggle[] = [
  { key: "mail_enabled", label: "Mail outbound", hint: "Outreach por SMTP", icon: Send, category: "mail" },
  { key: "mail_inbound_sync_enabled", label: "Mail inbound", hint: "Sync bandeja de entrada", icon: Inbox, category: "mail" },
  { key: "require_approved_drafts", label: "Requiere aprobacion", hint: "Revision antes de envio", icon: ShieldCheck, category: "mail" },
  { key: "whatsapp_outreach_enabled", label: "WhatsApp outreach", hint: "Drafts de WhatsApp en pipeline", icon: MessageCircle, category: "whatsapp" },
  { key: "notifications_enabled", label: "Notificaciones", hint: "Alertas globales del sistema", icon: Bell, category: "whatsapp" },
  { key: "telegram_alerts_enabled", label: "Telegram alertas", hint: "Notificaciones por Telegram", icon: Bell, category: "whatsapp" },
];
