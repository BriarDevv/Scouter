"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Bot,
  BrainCircuit,
  Building2,
  Cpu,
  ExternalLink,
  Globe,
  KeyRound,
  Loader2,
  Mail,
  RefreshCw,
  Save,
  Settings,
  ShieldCheck,
  ToggleLeft,
  ToggleRight,
  TriangleAlert,
  User,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import {
  getCredentialsStatus,
  getLLMSettings,
  getMailSettings,
  getOperationalSettings,
  updateOperationalSettings,
} from "@/lib/api/client";
import type {
  CredentialsStatus,
  LLMSettings,
  MailSettings,
  OperationalSettings,
} from "@/types";

// ─── Shared primitives ────────────────────────────────────────────────

function SectionCard({
  title,
  description,
  icon: Icon,
  children,
}: {
  title: string;
  description?: string;
  icon?: typeof Settings;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-start gap-3">
        {Icon && (
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-white">
            <Icon className="h-4 w-4" />
          </div>
        )}
        <div>
          <h2 className="font-heading text-base font-semibold text-slate-900">{title}</h2>
          {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-3 last:border-b-0">
      <span className="text-sm text-slate-500">{label}</span>
      <div className="text-right text-sm font-medium text-slate-900">{value}</div>
    </div>
  );
}

function StatusPill({
  label,
  tone,
}: {
  label: string;
  tone: "positive" | "warning" | "neutral" | "danger";
}) {
  const styles = {
    positive: "bg-emerald-50 text-emerald-700",
    warning: "bg-amber-50 text-amber-700",
    neutral: "bg-slate-100 text-slate-600",
    danger: "bg-rose-50 text-rose-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${styles[tone]}`}>
      {label}
    </span>
  );
}

function FieldRow({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5 border-b border-slate-100 py-3 last:border-b-0">
      <label className="text-sm font-medium text-slate-700">{label}</label>
      {hint && <p className="text-xs text-slate-400">{hint}</p>}
      {children}
    </div>
  );
}

function TextInput({
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
    />
  );
}

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex items-center gap-2 text-sm text-slate-700"
    >
      {checked ? (
        <ToggleRight className="h-5 w-5 text-emerald-600" />
      ) : (
        <ToggleLeft className="h-5 w-5 text-slate-400" />
      )}
      {label && <span>{label}</span>}
    </button>
  );
}

function SaveButton({
  onClick,
  saving,
  saved,
  disabled,
}: {
  onClick: () => void;
  saving: boolean;
  saved: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={saving || disabled}
      className="flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
    >
      {saving ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : saved ? (
        <ShieldCheck className="h-4 w-4 text-emerald-400" />
      ) : (
        <Save className="h-4 w-4" />
      )}
      {saving ? "Guardando\u2026" : saved ? "Guardado" : "Guardar"}
    </button>
  );
}

function useSave(
  key: string,
  getData: () => Partial<OperationalSettings>,
  onSaved: (updated: OperationalSettings) => void
) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const savedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const save = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateOperationalSettings(getData());
      onSaved(updated);
      setSaved(true);
      if (savedTimer.current) clearTimeout(savedTimer.current);
      savedTimer.current = setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar.");
    } finally {
      setSaving(false);
    }
  }, [getData, onSaved]);

  return { save, saving, saved, error };
}

// ─── LLM Section (read-only) ─────────────────────────────────────────

function LLMSection({ data }: { data: LLMSettings }) {
  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
      <SectionCard
        title="Modelos activos"
        description="Configuraci\u00f3n LLM read-only desde env."
        icon={Bot}
      >
        <div className="space-y-3">
          {[
            { label: "Leader", model: data.leader_model, Icon: BrainCircuit },
            { label: "Executor", model: data.executor_model, Icon: Cpu },
            { label: "Reviewer", model: data.reviewer_model, Icon: ShieldCheck },
          ].map(({ label, model, Icon }) => (
            <div
              key={label}
              className="flex items-center justify-between rounded-2xl border border-slate-100 bg-slate-50/70 px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-900 text-white">
                  <Icon className="h-4 w-4" />
                </div>
                <span className="text-sm font-medium text-slate-900">{label}</span>
              </div>
              <code className="rounded-lg bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm">
                {model ?? "No configurado"}
              </code>
            </div>
          ))}
        </div>
      </SectionCard>
      <SectionCard title="Detalles" icon={Settings}>
        <MetaRow label="Provider" value={data.provider} />
        <MetaRow label="Base URL" value={<code className="text-xs">{data.base_url}</code>} />
        <MetaRow label="Timeout" value={`${data.timeout_seconds}s`} />
        <MetaRow label="Reintentos" value={data.max_retries} />
        <MetaRow
          label="Cat\u00e1logo"
          value={
            <div className="flex flex-wrap justify-end gap-1">
              {data.supported_models.map((m) => (
                <code key={m} className="rounded-lg bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                  {m}
                </code>
              ))}
            </div>
          }
        />
      </SectionCard>
    </div>
  );
}

// ─── Credentials Section (read-only presence) ────────────────────────

function CredentialsSection({ data }: { data: CredentialsStatus }) {
  const renderItems = (items: CredentialsStatus["smtp"]) => (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.key} className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <KeyRound className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-sm text-slate-700">{item.label}</span>
          </div>
          <StatusPill
            label={item.set ? "Configurado" : "Faltante"}
            tone={item.set ? "positive" : item.required ? "danger" : "neutral"}
          />
        </div>
      ))}
    </div>
  );

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <SectionCard
        title="Credenciales SMTP"
        description="Estado de presencia \u2014 valores nunca expuestos."
        icon={KeyRound}
      >
        <div className="mb-4 flex gap-2">
          <StatusPill
            label={data.all_smtp_ready ? "SMTP listo" : "SMTP incompleto"}
            tone={data.all_smtp_ready ? "positive" : "warning"}
          />
        </div>
        {renderItems(data.smtp)}
        <p className="mt-4 text-xs text-slate-400">
          Para actualizar secretos, edit\u00e1 el archivo <code>.env</code> y reinici\u00e1 el servidor.
        </p>
      </SectionCard>
      <SectionCard
        title="Credenciales IMAP"
        description="Estado de presencia \u2014 valores nunca expuestos."
        icon={KeyRound}
      >
        <div className="mb-4 flex gap-2">
          <StatusPill
            label={data.all_imap_ready ? "IMAP listo" : "IMAP incompleto"}
            tone={data.all_imap_ready ? "positive" : "warning"}
          />
        </div>
        {renderItems(data.imap)}
        <p className="mt-4 text-xs text-slate-400">
          Para actualizar secretos, edit\u00e1 el archivo <code>.env</code> y reinici\u00e1 el servidor.
        </p>
      </SectionCard>
    </div>
  );
}

// ─── Brand / Signature Section ───────────────────────────────────────

function BrandSection({
  data,
  onSaved,
}: {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}) {
  const [form, setForm] = useState({
    brand_name: data.brand_name ?? "",
    signature_name: data.signature_name ?? "",
    signature_role: data.signature_role ?? "",
    signature_company: data.signature_company ?? "",
    portfolio_url: data.portfolio_url ?? "",
    website_url: data.website_url ?? "",
    calendar_url: data.calendar_url ?? "",
    signature_cta: data.signature_cta ?? "",
    signature_include_portfolio: data.signature_include_portfolio,
    default_outreach_tone: data.default_outreach_tone,
    default_reply_tone: data.default_reply_tone,
    default_closing_line: data.default_closing_line ?? "",
  });

  const set = (k: string) => (v: string | boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const getData = useCallback(
    () => ({
      brand_name: form.brand_name || null,
      signature_name: form.signature_name || null,
      signature_role: form.signature_role || null,
      signature_company: form.signature_company || null,
      portfolio_url: form.portfolio_url || null,
      website_url: form.website_url || null,
      calendar_url: form.calendar_url || null,
      signature_cta: form.signature_cta || null,
      signature_include_portfolio: form.signature_include_portfolio,
      default_outreach_tone: form.default_outreach_tone || "profesional",
      default_reply_tone: form.default_reply_tone || "profesional",
      default_closing_line: form.default_closing_line || null,
    }),
    [form]
  );

  const { save, saving, saved, error } = useSave("brand", getData, onSaved);

  return (
    <SectionCard
      title="Marca / Firma"
      description="Datos del emisor que se inyectan en drafts de outreach y respuestas asistidas."
      icon={Building2}
    >
      <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
        <div>
          <FieldRow label="Nombre comercial" hint="Nombre de la marca o agencia">
            <TextInput value={form.brand_name} onChange={set("brand_name")} placeholder="ej. BriarDev" />
          </FieldRow>
          <FieldRow label="Nombre del firmante">
            <TextInput value={form.signature_name} onChange={set("signature_name")} placeholder="ej. Mateo" />
          </FieldRow>
          <FieldRow label="Rol / Cargo">
            <TextInput value={form.signature_role} onChange={set("signature_role")} placeholder="ej. Desarrollador Web" />
          </FieldRow>
          <FieldRow label="Empresa en firma">
            <TextInput value={form.signature_company} onChange={set("signature_company")} placeholder="ej. BriarDev" />
          </FieldRow>
          <FieldRow label="CTA corta" hint="Llamada a la acci\u00f3n al final del email">
            <TextInput value={form.signature_cta} onChange={set("signature_cta")} placeholder="ej. \u00bfAgendamos una charla de 15 min?" />
          </FieldRow>
          <FieldRow label="L\u00ednea de cierre" hint="Frase final antes de la firma">
            <TextInput value={form.default_closing_line} onChange={set("default_closing_line")} placeholder="ej. Quedo atento, saludos" />
          </FieldRow>
        </div>
        <div>
          <FieldRow label="Portfolio URL">
            <TextInput value={form.portfolio_url} onChange={set("portfolio_url")} placeholder="https://briardev.xyz/portfolio" type="url" />
          </FieldRow>
          <FieldRow label="Sitio web">
            <TextInput value={form.website_url} onChange={set("website_url")} placeholder="https://briardev.xyz" type="url" />
          </FieldRow>
          <FieldRow label="URL de calendario" hint="Calendly u otro link de agenda">
            <TextInput value={form.calendar_url} onChange={set("calendar_url")} placeholder="https://cal.com/..." type="url" />
          </FieldRow>
          <FieldRow label="Tono outreach">
            <select
              value={form.default_outreach_tone}
              onChange={(e) => set("default_outreach_tone")(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-400 focus:bg-white"
            >
              {["profesional", "cercano", "consultivo", "breve", "emp\u00e1tico"].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </FieldRow>
          <FieldRow label="Tono de respuestas">
            <select
              value={form.default_reply_tone}
              onChange={(e) => set("default_reply_tone")(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-400 focus:bg-white"
            >
              {["profesional", "cercano", "consultivo", "breve", "emp\u00e1tico"].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </FieldRow>
          <FieldRow label="Incluir portfolio en firma">
            <Toggle
              checked={form.signature_include_portfolio}
              onChange={set("signature_include_portfolio") as (v: boolean) => void}
              label={form.signature_include_portfolio ? "S\u00ed" : "No"}
            />
          </FieldRow>
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between">
        {error && <p className="text-sm text-rose-600">{error}</p>}
        {!error && <span />}
        <SaveButton onClick={save} saving={saving} saved={saved} />
      </div>
    </SectionCard>
  );
}

// ─── Mail Outbound Section ────────────────────────────────────────────

function MailOutboundSection({
  data,
  mailData,
  onSaved,
}: {
  data: OperationalSettings;
  mailData: MailSettings;
  onSaved: (updated: OperationalSettings) => void;
}) {
  const [form, setForm] = useState({
    mail_enabled: data.mail_enabled ?? false,
    mail_from_email: data.mail_from_email ?? "",
    mail_from_name: data.mail_from_name ?? "",
    mail_reply_to: data.mail_reply_to ?? "",
    mail_send_timeout_seconds: String(data.mail_send_timeout_seconds ?? ""),
    require_approved_drafts: data.require_approved_drafts,
  });

  const set = (k: string) => (v: string | boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const getData = useCallback(
    () => ({
      mail_enabled: form.mail_enabled,
      mail_from_email: form.mail_from_email || null,
      mail_from_name: form.mail_from_name || null,
      mail_reply_to: form.mail_reply_to || null,
      mail_send_timeout_seconds: form.mail_send_timeout_seconds
        ? parseInt(form.mail_send_timeout_seconds, 10)
        : null,
      require_approved_drafts: form.require_approved_drafts,
    }),
    [form]
  );

  const { save, saving, saved, error } = useSave("mail_outbound", getData, onSaved);

  return (
    <SectionCard
      title="Mail outbound"
      description="Configuraci\u00f3n operativa de env\u00edo. Credenciales SMTP siguen en .env."
      icon={Mail}
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <StatusPill
          label={mailData.outbound.ready ? "Ready" : "No listo"}
          tone={mailData.outbound.ready ? "positive" : "warning"}
        />
        <StatusPill
          label={mailData.outbound.configured ? "Configurado" : "Incompleto"}
          tone={mailData.outbound.configured ? "positive" : "warning"}
        />
        {mailData.outbound.missing_requirements.length > 0 && (
          <StatusPill
            label={`Faltan ${mailData.outbound.missing_requirements.length} credenciales`}
            tone="danger"
          />
        )}
      </div>
      <FieldRow label="Habilitar mail outbound">
        <Toggle checked={form.mail_enabled} onChange={set("mail_enabled") as (v: boolean) => void} label={form.mail_enabled ? "Habilitado" : "Deshabilitado"} />
      </FieldRow>
      <FieldRow label="From Email" hint="Override sobre MAIL_FROM_EMAIL en .env">
        <TextInput value={form.mail_from_email} onChange={set("mail_from_email")} placeholder={mailData.outbound.from_email ?? "Usa valor de .env"} type="email" />
      </FieldRow>
      <FieldRow label="From Name">
        <TextInput value={form.mail_from_name} onChange={set("mail_from_name")} placeholder={mailData.outbound.from_name} />
      </FieldRow>
      <FieldRow label="Reply-To">
        <TextInput value={form.mail_reply_to} onChange={set("mail_reply_to")} placeholder={mailData.outbound.reply_to ?? "Sin reply-to"} type="email" />
      </FieldRow>
      <FieldRow label="Timeout de env\u00edo (segundos)">
        <TextInput value={form.mail_send_timeout_seconds} onChange={set("mail_send_timeout_seconds")} placeholder={String(mailData.outbound.send_timeout_seconds)} type="number" />
      </FieldRow>
      <FieldRow label="Requerir drafts aprobados">
        <Toggle checked={form.require_approved_drafts} onChange={set("require_approved_drafts") as (v: boolean) => void} label={form.require_approved_drafts ? "Solo drafts approved" : "Sin restricci\u00f3n"} />
      </FieldRow>
      <div className="mt-4 flex items-center justify-between">
        {error && <p className="text-sm text-rose-600">{error}</p>}
        {!error && <span />}
        <SaveButton onClick={save} saving={saving} saved={saved} />
      </div>
    </SectionCard>
  );
}

// ─── Mail Inbound Section ─────────────────────────────────────────────

function MailInboundSection({
  data,
  mailData,
  onSaved,
}: {
  data: OperationalSettings;
  mailData: MailSettings;
  onSaved: (updated: OperationalSettings) => void;
}) {
  const [form, setForm] = useState({
    mail_inbound_sync_enabled: data.mail_inbound_sync_enabled ?? false,
    mail_inbound_mailbox: data.mail_inbound_mailbox ?? "",
    mail_inbound_sync_limit: String(data.mail_inbound_sync_limit ?? ""),
    mail_inbound_timeout_seconds: String(data.mail_inbound_timeout_seconds ?? ""),
    mail_inbound_search_criteria: data.mail_inbound_search_criteria ?? "",
  });

  const set = (k: string) => (v: string | boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const getData = useCallback(
    () => ({
      mail_inbound_sync_enabled: form.mail_inbound_sync_enabled,
      mail_inbound_mailbox: form.mail_inbound_mailbox || null,
      mail_inbound_sync_limit: form.mail_inbound_sync_limit ? parseInt(form.mail_inbound_sync_limit, 10) : null,
      mail_inbound_timeout_seconds: form.mail_inbound_timeout_seconds ? parseInt(form.mail_inbound_timeout_seconds, 10) : null,
      mail_inbound_search_criteria: form.mail_inbound_search_criteria || null,
    }),
    [form]
  );

  const { save, saving, saved, error } = useSave("mail_inbound", getData, onSaved);

  return (
    <SectionCard
      title="Mail inbound"
      description="Configuraci\u00f3n del canal de lectura de inbox. Credenciales IMAP siguen en .env."
      icon={Mail}
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <StatusPill
          label={mailData.inbound.ready ? "Ready" : "No listo"}
          tone={mailData.inbound.ready ? "positive" : "warning"}
        />
        <StatusPill
          label={mailData.inbound.account ?? "Sin cuenta"}
          tone={mailData.inbound.account ? "neutral" : "warning"}
        />
        {mailData.inbound.last_sync && (
          <StatusPill label={`Sync: ${mailData.inbound.last_sync.status}`} tone="neutral" />
        )}
      </div>
      <FieldRow label="Habilitar sync inbound">
        <Toggle checked={form.mail_inbound_sync_enabled} onChange={set("mail_inbound_sync_enabled") as (v: boolean) => void} label={form.mail_inbound_sync_enabled ? "Habilitado" : "Deshabilitado"} />
      </FieldRow>
      <FieldRow label="Mailbox" hint="Override sobre MAIL_IMAP_MAILBOX en .env">
        <TextInput value={form.mail_inbound_mailbox} onChange={set("mail_inbound_mailbox")} placeholder={mailData.inbound.mailbox} />
      </FieldRow>
      <FieldRow label="Sync limit">
        <TextInput value={form.mail_inbound_sync_limit} onChange={set("mail_inbound_sync_limit")} placeholder={String(mailData.inbound.sync_limit)} type="number" />
      </FieldRow>
      <FieldRow label="Timeout (segundos)">
        <TextInput value={form.mail_inbound_timeout_seconds} onChange={set("mail_inbound_timeout_seconds")} placeholder={String(mailData.inbound.timeout_seconds)} type="number" />
      </FieldRow>
      <FieldRow label="Search criteria">
        <TextInput value={form.mail_inbound_search_criteria} onChange={set("mail_inbound_search_criteria")} placeholder={mailData.inbound.search_criteria} />
      </FieldRow>
      {mailData.inbound.last_sync && (
        <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50/70 p-4">
          <p className="mb-3 text-xs font-medium text-slate-500">\u00daltima sync persistida</p>
          <div className="grid grid-cols-3 gap-2 text-sm">
            {[
              ["Fetched", mailData.inbound.last_sync.counts.fetched],
              ["New", mailData.inbound.last_sync.counts.new],
              ["Matched", mailData.inbound.last_sync.counts.matched],
            ].map(([k, v]) => (
              <div key={String(k)} className="rounded-xl bg-white px-3 py-2">
                <p className="text-xs text-slate-400">{k}</p>
                <p className="font-semibold text-slate-900">{v}</p>
              </div>
            ))}
          </div>
          {mailData.inbound.last_sync.at && (
            <p className="mt-2 text-xs text-slate-400">
              <RelativeTime date={mailData.inbound.last_sync.at} />
            </p>
          )}
        </div>
      )}
      <div className="mt-4 flex items-center justify-between">
        {error && <p className="text-sm text-rose-600">{error}</p>}
        {!error && <span />}
        <SaveButton onClick={save} saving={saving} saved={saved} />
      </div>
    </SectionCard>
  );
}

// ─── Rules / Automation Section ───────────────────────────────────────

function RulesSection({
  data,
  onSaved,
}: {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}) {
  const [form, setForm] = useState({
    require_approved_drafts: data.require_approved_drafts,
    auto_classify_inbound: data.auto_classify_inbound,
    reply_assistant_enabled: data.reply_assistant_enabled,
    reviewer_enabled: data.reviewer_enabled,
    reviewer_confidence_threshold: String(data.reviewer_confidence_threshold),
    prioritize_quote_replies: data.prioritize_quote_replies,
    prioritize_meeting_replies: data.prioritize_meeting_replies,
    allow_openclaw_briefs: data.allow_openclaw_briefs,
    allow_reply_assistant_generation: data.allow_reply_assistant_generation,
  });

  const set = (k: string) => (v: string | boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const getData = useCallback(
    () => ({
      require_approved_drafts: form.require_approved_drafts,
      auto_classify_inbound: form.auto_classify_inbound,
      reply_assistant_enabled: form.reply_assistant_enabled,
      reviewer_enabled: form.reviewer_enabled,
      reviewer_confidence_threshold: parseFloat(form.reviewer_confidence_threshold) || 0.7,
      prioritize_quote_replies: form.prioritize_quote_replies,
      prioritize_meeting_replies: form.prioritize_meeting_replies,
      allow_openclaw_briefs: form.allow_openclaw_briefs,
      allow_reply_assistant_generation: form.allow_reply_assistant_generation,
    }),
    [form]
  );

  const { save, saving, saved, error } = useSave("rules", getData, onSaved);

  const rules: Array<{ key: keyof typeof form; label: string; hint?: string }> = [
    { key: "require_approved_drafts", label: "Requerir aprobaci\u00f3n de drafts", hint: "Solo los drafts aprobados se pueden enviar" },
    { key: "auto_classify_inbound", label: "Auto-clasificar inbound", hint: "Clasificar replies autom\u00e1ticamente al sync" },
    { key: "reply_assistant_enabled", label: "Reply assistant habilitado" },
    { key: "reviewer_enabled", label: "Reviewer habilitado", hint: "Activa revisi\u00f3n profunda por el modelo reviewer" },
    { key: "prioritize_quote_replies", label: "Priorizar replies con pedido de cotizaci\u00f3n" },
    { key: "prioritize_meeting_replies", label: "Priorizar replies con pedido de reuni\u00f3n" },
    { key: "allow_openclaw_briefs", label: "Permitir briefs de OpenClaw" },
    { key: "allow_reply_assistant_generation", label: "Permitir generaci\u00f3n de reply assistant" },
  ];

  return (
    <SectionCard
      title="Reglas / Automatizaci\u00f3n"
      description="Control operativo del comportamiento del sistema."
      icon={Settings}
    >
      <div className="space-y-0">
        {rules.map(({ key, label, hint }) => (
          <FieldRow key={key} label={label} hint={hint}>
            <Toggle
              checked={Boolean(form[key])}
              onChange={set(key) as (v: boolean) => void}
              label={Boolean(form[key]) ? "Activo" : "Inactivo"}
            />
          </FieldRow>
        ))}
        <FieldRow label="Umbral de confianza del reviewer" hint="Valor entre 0 y 1 (ej. 0.7)">
          <TextInput
            value={form.reviewer_confidence_threshold}
            onChange={set("reviewer_confidence_threshold")}
            placeholder="0.7"
            type="number"
          />
        </FieldRow>
      </div>
      <div className="mt-4 flex items-center justify-between">
        {error && <p className="text-sm text-rose-600">{error}</p>}
        {!error && <span />}
        <SaveButton onClick={save} saving={saving} saved={saved} />
      </div>
    </SectionCard>
  );
}

// ─── Page ──────────────────────────────────────────────────────────────

type TabId = "llm" | "brand" | "mail_out" | "mail_in" | "rules" | "credentials";

const TABS: Array<{ id: TabId; label: string }> = [
  { id: "llm", label: "LLM" },
  { id: "brand", label: "Marca / Firma" },
  { id: "mail_out", label: "Mail outbound" },
  { id: "mail_in", label: "Mail inbound" },
  { id: "rules", label: "Reglas" },
  { id: "credentials", label: "Credenciales" },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("brand");
  const [llmData, setLlmData] = useState<LLMSettings | null>(null);
  const [mailData, setMailData] = useState<MailSettings | null>(null);
  const [opData, setOpData] = useState<OperationalSettings | null>(null);
  const [credsData, setCredsData] = useState<CredentialsStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    Promise.allSettled([
      getLLMSettings(),
      getMailSettings(),
      getOperationalSettings(),
      getCredentialsStatus(),
    ]).then(([llm, mail, op, creds]) => {
      if (!active) return;
      if (llm.status === "fulfilled") setLlmData(llm.value);
      if (mail.status === "fulfilled") setMailData(mail.value);
      if (op.status === "fulfilled") setOpData(op.value);
      if (creds.status === "fulfilled") setCredsData(creds.value);
      if (
        llm.status === "rejected" &&
        mail.status === "rejected" &&
        op.status === "rejected"
      ) {
        setError("No se pudo conectar con el backend.");
      }
      setLoading(false);
    });

    return () => { active = false; };
  }, []);

  const handleSaved = (updated: OperationalSettings) => setOpData(updated);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Configuraci\u00f3n"
        description="Configuraci\u00f3n operativa real del sistema. LLM y credenciales son read-only desde env."
      />

      {loading && (
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando configuraci\u00f3n\u2026
        </div>
      )}

      {!loading && error && (
        <EmptyState icon={Settings} title="Sin configuraci\u00f3n disponible" description={error} />
      )}

      {!loading && !error && (
        <>
          {/* Tab nav */}
          <div className="flex flex-wrap gap-1 rounded-2xl border border-slate-200 bg-slate-50 p-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                  activeTab === tab.id
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div>
            {activeTab === "llm" && llmData && <LLMSection data={llmData} />}
            {activeTab === "brand" && opData && (
              <BrandSection data={opData} onSaved={handleSaved} />
            )}
            {activeTab === "mail_out" && opData && mailData && (
              <MailOutboundSection data={opData} mailData={mailData} onSaved={handleSaved} />
            )}
            {activeTab === "mail_in" && opData && mailData && (
              <MailInboundSection data={opData} mailData={mailData} onSaved={handleSaved} />
            )}
            {activeTab === "rules" && opData && (
              <RulesSection data={opData} onSaved={handleSaved} />
            )}
            {activeTab === "credentials" && credsData && (
              <CredentialsSection data={credsData} />
            )}

            {/* Fallback if data missing for tab */}
            {(activeTab === "llm" && !llmData) ||
            (activeTab === "brand" && !opData) ||
            (activeTab === "mail_out" && (!opData || !mailData)) ||
            (activeTab === "mail_in" && (!opData || !mailData)) ||
            (activeTab === "rules" && !opData) ||
            (activeTab === "credentials" && !credsData) ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
                <div className="flex items-center gap-2">
                  <TriangleAlert className="h-4 w-4 text-amber-500" />
                  No se pudieron cargar los datos para esta secci\u00f3n.
                </div>
              </div>
            ) : null}
          </div>

          {/* Operational settings last update */}
          {opData?.updated_at && (
            <p className="text-xs text-slate-400">
              \u00daltima actualizaci\u00f3n de settings operativos:{" "}
              <RelativeTime date={opData.updated_at} />
            </p>
          )}
        </>
      )}
    </div>
  );
}
