"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Bot,
  BrainCircuit,
  Building2,
  CheckCircle2,
  Cpu,
  ExternalLink,
  Eye,
  EyeOff,
  Globe,
  KeyRound,
  Loader2,
  Lock,
  Mail,
  RefreshCw,
  Save,
  Settings,
  ShieldCheck,
  ToggleLeft,
  ToggleRight,
  TriangleAlert,
  XCircle,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import {
  getMailCredentials,
  getLLMSettings,
  getMailSettings,
  getOperationalSettings,
  getSetupStatus,
  testImapConnection,
  testSmtpConnection,
  updateMailCredentials,
  updateOperationalSettings,
} from "@/lib/api/client";
import type {
  ConnectionTestResult,
  LLMSettings,
  MailCredentials,
  MailSettings,
  OperationalSettings,
  SetupStatus,
} from "@/types";

// ─── Provider presets ─────────────────────────────────────────────────

type MailProvider = "gmail" | "outlook" | "zoho" | "custom";

const SMTP_PRESETS: Record<
  MailProvider,
  { host: string; port: number; ssl: boolean; starttls: boolean } | null
> = {
  gmail: { host: "smtp.gmail.com", port: 587, ssl: false, starttls: true },
  outlook: { host: "smtp.office365.com", port: 587, ssl: false, starttls: true },
  zoho: { host: "smtp.zoho.com", port: 587, ssl: false, starttls: true },
  custom: null,
};

const IMAP_PRESETS: Record<
  MailProvider,
  { host: string; port: number; ssl: boolean } | null
> = {
  gmail: { host: "imap.gmail.com", port: 993, ssl: true },
  outlook: { host: "outlook.office365.com", port: 993, ssl: true },
  zoho: { host: "imap.zoho.com", port: 993, ssl: true },
  custom: null,
};

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
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${styles[tone]}`}
    >
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
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  disabled?: boolean;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white disabled:opacity-50"
    />
  );
}

function PasswordInput({
  value,
  onChange,
  placeholder,
  alreadySet,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  alreadySet?: boolean;
}) {
  const [visible, setVisible] = useState(false);
  const isEmpty = value === "";
  return (
    <div className="relative">
      <input
        type={visible ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={
          alreadySet && isEmpty
            ? "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022  (ya configurado)"
            : (placeholder ?? "Nueva contrase\u00f1a")
        }
        className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 pr-20 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
      />
      <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
        {alreadySet && isEmpty && (
          <Lock className="h-3.5 w-3.5 text-emerald-500" />
        )}
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="rounded p-1 text-slate-400 hover:text-slate-600"
          tabIndex={-1}
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
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
  getData: () => Partial<OperationalSettings>,
  onSaved: (updated: OperationalSettings) => void
) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const save = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateOperationalSettings(getData());
      onSaved(updated);
      setSaved(true);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar.");
    } finally {
      setSaving(false);
    }
  }, [getData, onSaved]);

  return { save, saving, saved, error };
}

// ─── Provider Picker ─────────────────────────────────────────────────

function ProviderPicker({
  value,
  onChange,
}: {
  value: MailProvider;
  onChange: (p: MailProvider) => void;
}) {
  const options: Array<{ id: MailProvider; label: string }> = [
    { id: "gmail", label: "Gmail" },
    { id: "outlook", label: "Outlook" },
    { id: "zoho", label: "Zoho" },
    { id: "custom", label: "Custom" },
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => (
        <button
          key={opt.id}
          type="button"
          onClick={() => onChange(opt.id)}
          className={`rounded-xl border px-4 py-2 text-sm font-medium transition ${
            value === opt.id
              ? "border-slate-900 bg-slate-900 text-white"
              : "border-slate-200 bg-white text-slate-600 hover:border-slate-400"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

// ─── Connection Test Badge ────────────────────────────────────────────

function ConnectionTestBadge({
  lastAt,
  lastOk,
  lastError,
}: {
  lastAt: string | null;
  lastOk: boolean | null;
  lastError: string | null;
}) {
  if (!lastAt) {
    return <span className="text-xs text-slate-400">Sin prueba realizada</span>;
  }
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5">
        {lastOk ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        ) : (
          <XCircle className="h-4 w-4 text-rose-500" />
        )}
        <span
          className={`text-xs font-medium ${lastOk ? "text-emerald-700" : "text-rose-700"}`}
        >
          {lastOk ? "Conexi\u00f3n exitosa" : "Fall\u00f3"}
        </span>
        <span className="text-xs text-slate-400">
          &middot; <RelativeTime date={lastAt} />
        </span>
      </div>
      {!lastOk && lastError && (
        <p className="rounded-lg bg-rose-50 px-2 py-1 text-xs text-rose-600">{lastError}</p>
      )}
    </div>
  );
}

// ─── Test Button ──────────────────────────────────────────────────────

function TestButton({
  onTest,
  label,
}: {
  onTest: () => Promise<ConnectionTestResult>;
  label: string;
}) {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<ConnectionTestResult | null>(null);

  const run = async () => {
    setTesting(true);
    setResult(null);
    try {
      const r = await onTest();
      setResult(r);
    } catch {
      setResult({ ok: false, error: "Error de red al probar conexi\u00f3n.", sample_count: null });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={run}
        disabled={testing}
        className="flex w-fit items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400 disabled:opacity-50"
      >
        {testing ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        {testing ? "Probando\u2026" : label}
      </button>
      {result && (
        <div
          className={`flex items-center gap-1.5 text-xs font-medium ${result.ok ? "text-emerald-700" : "text-rose-700"}`}
        >
          {result.ok ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          ) : (
            <XCircle className="h-4 w-4 text-rose-500" />
          )}
          {result.ok
            ? `Conexi\u00f3n OK${result.sample_count != null ? ` \u00b7 ${result.sample_count} mensajes encontrados` : ""}`
            : result.error}
        </div>
      )}
    </div>
  );
}

// ─── Setup Checklist ──────────────────────────────────────────────────

function SetupChecklist({
  data,
  onTabChange,
}: {
  data: SetupStatus;
  onTabChange: (tab: TabId) => void;
}) {
  const statusIcon = (s: string) => {
    if (s === "complete") return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
    if (s === "warning") return <TriangleAlert className="h-5 w-5 text-amber-500" />;
    if (s === "incomplete") return <XCircle className="h-5 w-5 text-rose-400" />;
    return <div className="h-5 w-5 rounded-full border-2 border-slate-200" />;
  };

  const actionTabMap: Record<string, TabId> = {
    brand: "brand",
    mail_out: "mail_out",
    mail_in: "mail_in",
    rules: "rules",
  };

  const overallBg =
    data.overall === "ready"
      ? "bg-emerald-50 border-emerald-200"
      : data.overall === "warning"
        ? "bg-amber-50 border-amber-200"
        : "bg-slate-50 border-slate-200";

  const overallLabel =
    data.overall === "ready"
      ? "Sistema listo para operar"
      : data.overall === "warning"
        ? "Listo con advertencias"
        : "Configuraci\u00f3n incompleta";

  const overallText =
    data.overall === "ready"
      ? "text-emerald-700"
      : data.overall === "warning"
        ? "text-amber-700"
        : "text-slate-600";

  return (
    <div className="space-y-6">
      <div className={`rounded-2xl border p-5 ${overallBg}`}>
        <div className="flex items-center gap-3">
          {data.overall === "ready" ? (
            <CheckCircle2 className="h-6 w-6 text-emerald-500" />
          ) : data.overall === "warning" ? (
            <TriangleAlert className="h-6 w-6 text-amber-500" />
          ) : (
            <XCircle className="h-6 w-6 text-rose-400" />
          )}
          <div>
            <p className={`font-semibold ${overallText}`}>{overallLabel}</p>
            <div className="mt-1 flex gap-3 text-xs">
              <span className={data.ready_to_send ? "text-emerald-600" : "text-slate-400"}>
                {data.ready_to_send ? "\u2713" : "\u25cb"} Env\u00edo listo
              </span>
              <span className={data.ready_to_receive ? "text-emerald-600" : "text-slate-400"}>
                {data.ready_to_receive ? "\u2713" : "\u25cb"} Recepci\u00f3n lista
              </span>
            </div>
          </div>
        </div>
      </div>
      <div className="space-y-3">
        {data.steps.map((step) => (
          <div
            key={step.id}
            className="flex items-start gap-4 rounded-2xl border border-slate-100 bg-white p-4"
          >
            <div className="mt-0.5 shrink-0">{statusIcon(step.status)}</div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-900">{step.label}</p>
              {step.detail && (
                <p className="mt-0.5 text-xs text-slate-500">{step.detail}</p>
              )}
            </div>
            {step.action && actionTabMap[step.id] && (
              <button
                type="button"
                onClick={() => onTabChange(actionTabMap[step.id])}
                className="shrink-0 rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-slate-400 hover:text-slate-900"
              >
                {step.action}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Signature Preview ────────────────────────────────────────────────

function SignaturePreview({
  form,
}: {
  form: {
    signature_name: string;
    signature_role: string;
    signature_company: string;
    portfolio_url: string;
    website_url: string;
    calendar_url: string;
    signature_cta: string;
    default_closing_line: string;
    signature_include_portfolio: boolean;
  };
}) {
  const hasContent = form.signature_name || form.signature_role || form.signature_company;
  if (!hasContent) {
    return (
      <div className="flex items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8">
        <p className="text-sm text-slate-400">
          Complet\u00e1 los datos para ver la preview
        </p>
      </div>
    );
  }
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-400">
        Preview de firma
      </p>
      <div className="border-t border-slate-200 pt-4 font-mono text-sm text-slate-700">
        {form.default_closing_line && (
          <p className="mb-3 text-slate-600">{form.default_closing_line}</p>
        )}
        {form.signature_name && (
          <p className="font-semibold text-slate-900">{form.signature_name}</p>
        )}
        {form.signature_role && <p className="text-slate-600">{form.signature_role}</p>}
        {form.signature_company && <p className="text-slate-600">{form.signature_company}</p>}
        {(form.website_url || form.portfolio_url) && (
          <div className="mt-2 flex flex-col gap-0.5 text-xs text-slate-500">
            {form.website_url && (
              <span className="flex items-center gap-1">
                <Globe className="h-3 w-3" />
                {form.website_url}
              </span>
            )}
            {form.signature_include_portfolio && form.portfolio_url && (
              <span className="flex items-center gap-1">
                <ExternalLink className="h-3 w-3" />
                Portfolio: {form.portfolio_url}
              </span>
            )}
            {form.calendar_url && (
              <span className="flex items-center gap-1 text-slate-400">
                {form.calendar_url}
              </span>
            )}
          </div>
        )}
        {form.signature_cta && (
          <p className="mt-3 italic text-slate-500">{form.signature_cta}</p>
        )}
      </div>
    </div>
  );
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
                <code
                  key={m}
                  className="rounded-lg bg-slate-100 px-2 py-0.5 text-xs text-slate-700"
                >
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

  const { save, saving, saved, error } = useSave(getData, onSaved);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr,0.65fr]">
      <SectionCard
        title="Marca / Firma"
        description="Datos del emisor que se inyectan en drafts de outreach y respuestas asistidas."
        icon={Building2}
      >
        <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
          <div>
            <FieldRow label="Nombre comercial" hint="Nombre de la marca o agencia">
              <TextInput
                value={form.brand_name}
                onChange={set("brand_name")}
                placeholder="ej. BriarDev"
              />
            </FieldRow>
            <FieldRow label="Nombre del firmante">
              <TextInput
                value={form.signature_name}
                onChange={set("signature_name")}
                placeholder="ej. Mateo"
              />
            </FieldRow>
            <FieldRow label="Rol / Cargo">
              <TextInput
                value={form.signature_role}
                onChange={set("signature_role")}
                placeholder="ej. Desarrollador Web"
              />
            </FieldRow>
            <FieldRow label="Empresa en firma">
              <TextInput
                value={form.signature_company}
                onChange={set("signature_company")}
                placeholder="ej. BriarDev"
              />
            </FieldRow>
            <FieldRow label="CTA corta" hint="Llamada a la acci\u00f3n al final del email">
              <TextInput
                value={form.signature_cta}
                onChange={set("signature_cta")}
                placeholder="ej. \u00bfAgendamos una charla de 15 min?"
              />
            </FieldRow>
            <FieldRow label="L\u00ednea de cierre" hint="Frase final antes de la firma">
              <TextInput
                value={form.default_closing_line}
                onChange={set("default_closing_line")}
                placeholder="ej. Quedo atento, saludos"
              />
            </FieldRow>
          </div>
          <div>
            <FieldRow label="Portfolio URL">
              <TextInput
                value={form.portfolio_url}
                onChange={set("portfolio_url")}
                placeholder="https://briardev.xyz/portfolio"
                type="url"
              />
            </FieldRow>
            <FieldRow label="Sitio web">
              <TextInput
                value={form.website_url}
                onChange={set("website_url")}
                placeholder="https://briardev.xyz"
                type="url"
              />
            </FieldRow>
            <FieldRow label="URL de calendario" hint="Calendly u otro link de agenda">
              <TextInput
                value={form.calendar_url}
                onChange={set("calendar_url")}
                placeholder="https://cal.com/..."
                type="url"
              />
            </FieldRow>
            <FieldRow label="Tono outreach">
              <select
                value={form.default_outreach_tone}
                onChange={(e) => set("default_outreach_tone")(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-400 focus:bg-white"
              >
                {["profesional", "cercano", "consultivo", "breve", "emp\u00e1tico"].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
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
                  <option key={t} value={t}>
                    {t}
                  </option>
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
          {error ? <p className="text-sm text-rose-600">{error}</p> : <span />}
          <SaveButton onClick={save} saving={saving} saved={saved} />
        </div>
      </SectionCard>
      <SignaturePreview form={form} />
    </div>
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

  const { save, saving, saved, error } = useSave(getData, onSaved);

  return (
    <SectionCard
      title="Mail de salida"
      description="Configuraci\u00f3n operativa del canal de env\u00edo. Credenciales SMTP en la pesta\u00f1a Credenciales."
      icon={Mail}
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <StatusPill
          label={mailData.outbound.ready ? "SMTP listo" : "SMTP no listo"}
          tone={mailData.outbound.ready ? "positive" : "warning"}
        />
        {mailData.outbound.missing_requirements.length > 0 && (
          <StatusPill
            label={`Falta: ${mailData.outbound.missing_requirements.join(", ")}`}
            tone="danger"
          />
        )}
      </div>
      <FieldRow label="Habilitar env\u00edo de mail">
        <Toggle
          checked={form.mail_enabled}
          onChange={set("mail_enabled") as (v: boolean) => void}
          label={form.mail_enabled ? "Habilitado" : "Deshabilitado"}
        />
      </FieldRow>
      <FieldRow label="From Email" hint="Override del campo MAIL_FROM_EMAIL">
        <TextInput
          value={form.mail_from_email}
          onChange={set("mail_from_email")}
          placeholder={mailData.outbound.from_email ?? "Usa valor de .env"}
          type="email"
        />
      </FieldRow>
      <FieldRow label="From Name">
        <TextInput
          value={form.mail_from_name}
          onChange={set("mail_from_name")}
          placeholder={mailData.outbound.from_name}
        />
      </FieldRow>
      <FieldRow label="Reply-To">
        <TextInput
          value={form.mail_reply_to}
          onChange={set("mail_reply_to")}
          placeholder={mailData.outbound.reply_to ?? "Sin reply-to"}
          type="email"
        />
      </FieldRow>
      <FieldRow label="Timeout de env\u00edo (seg)">
        <TextInput
          value={form.mail_send_timeout_seconds}
          onChange={set("mail_send_timeout_seconds")}
          placeholder={String(mailData.outbound.send_timeout_seconds)}
          type="number"
        />
      </FieldRow>
      <FieldRow label="Requerir aprobaci\u00f3n de drafts">
        <Toggle
          checked={form.require_approved_drafts}
          onChange={set("require_approved_drafts") as (v: boolean) => void}
          label={form.require_approved_drafts ? "Solo drafts aprobados" : "Sin restricci\u00f3n"}
        />
      </FieldRow>
      <div className="mt-4 flex items-center justify-between">
        {error ? <p className="text-sm text-rose-600">{error}</p> : <span />}
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
      mail_inbound_sync_limit: form.mail_inbound_sync_limit
        ? parseInt(form.mail_inbound_sync_limit, 10)
        : null,
      mail_inbound_timeout_seconds: form.mail_inbound_timeout_seconds
        ? parseInt(form.mail_inbound_timeout_seconds, 10)
        : null,
      mail_inbound_search_criteria: form.mail_inbound_search_criteria || null,
    }),
    [form]
  );

  const { save, saving, saved, error } = useSave(getData, onSaved);

  return (
    <SectionCard
      title="Bandeja de entrada"
      description="Configuraci\u00f3n del canal de lectura de inbox. Credenciales IMAP en la pesta\u00f1a Credenciales."
      icon={Mail}
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <StatusPill
          label={mailData.inbound.ready ? "IMAP listo" : "IMAP no listo"}
          tone={mailData.inbound.ready ? "positive" : "warning"}
        />
        {mailData.inbound.account && (
          <StatusPill label={mailData.inbound.account} tone="neutral" />
        )}
      </div>
      <FieldRow label="Habilitar sync de inbox">
        <Toggle
          checked={form.mail_inbound_sync_enabled}
          onChange={set("mail_inbound_sync_enabled") as (v: boolean) => void}
          label={form.mail_inbound_sync_enabled ? "Habilitado" : "Deshabilitado"}
        />
      </FieldRow>
      <FieldRow label="Mailbox" hint="Override del campo MAIL_IMAP_MAILBOX">
        <TextInput
          value={form.mail_inbound_mailbox}
          onChange={set("mail_inbound_mailbox")}
          placeholder={mailData.inbound.mailbox}
        />
      </FieldRow>
      <FieldRow label="L\u00edmite de sync">
        <TextInput
          value={form.mail_inbound_sync_limit}
          onChange={set("mail_inbound_sync_limit")}
          placeholder={String(mailData.inbound.sync_limit)}
          type="number"
        />
      </FieldRow>
      <FieldRow label="Timeout (seg)">
        <TextInput
          value={form.mail_inbound_timeout_seconds}
          onChange={set("mail_inbound_timeout_seconds")}
          placeholder={String(mailData.inbound.timeout_seconds)}
          type="number"
        />
      </FieldRow>
      <FieldRow label="Criterio de b\u00fasqueda IMAP">
        <TextInput
          value={form.mail_inbound_search_criteria}
          onChange={set("mail_inbound_search_criteria")}
          placeholder={mailData.inbound.search_criteria}
        />
      </FieldRow>
      {mailData.inbound.last_sync && (
        <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50/70 p-4">
          <p className="mb-3 text-xs font-medium text-slate-500">
            \u00daltima sync persistida
          </p>
          <div className="grid grid-cols-3 gap-2 text-sm">
            {(
              [
                ["Fetched", mailData.inbound.last_sync.counts.fetched],
                ["New", mailData.inbound.last_sync.counts.new],
                ["Matched", mailData.inbound.last_sync.counts.matched],
              ] as [string, number][]
            ).map(([k, v]) => (
              <div key={k} className="rounded-xl bg-white px-3 py-2">
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
        {error ? <p className="text-sm text-rose-600">{error}</p> : <span />}
        <SaveButton onClick={save} saving={saving} saved={saved} />
      </div>
    </SectionCard>
  );
}

// ─── Rules Section ────────────────────────────────────────────────────

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
      reviewer_confidence_threshold:
        parseFloat(form.reviewer_confidence_threshold) || 0.7,
      prioritize_quote_replies: form.prioritize_quote_replies,
      prioritize_meeting_replies: form.prioritize_meeting_replies,
      allow_openclaw_briefs: form.allow_openclaw_briefs,
      allow_reply_assistant_generation: form.allow_reply_assistant_generation,
    }),
    [form]
  );

  const { save, saving, saved, error } = useSave(getData, onSaved);

  const rules: Array<{ key: keyof typeof form; label: string; hint?: string }> = [
    {
      key: "require_approved_drafts",
      label: "Requerir aprobaci\u00f3n de drafts",
      hint: "Solo los drafts aprobados se pueden enviar",
    },
    { key: "auto_classify_inbound", label: "Clasificar replies autom\u00e1ticamente al sync" },
    { key: "reply_assistant_enabled", label: "Asistente de respuesta habilitado" },
    {
      key: "reviewer_enabled",
      label: "Revisor autom\u00e1tico habilitado",
      hint: "Activa revisi\u00f3n profunda por el modelo reviewer",
    },
    { key: "prioritize_quote_replies", label: "Priorizar replies con pedido de cotizaci\u00f3n" },
    { key: "prioritize_meeting_replies", label: "Priorizar replies con pedido de reuni\u00f3n" },
    { key: "allow_openclaw_briefs", label: "Permitir briefs de OpenClaw" },
    {
      key: "allow_reply_assistant_generation",
      label: "Permitir generaci\u00f3n de respuestas asistidas",
    },
  ];

  return (
    <SectionCard
      title="Reglas de automatizaci\u00f3n"
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
        <FieldRow
          label="Umbral de confianza del revisor"
          hint="Valor entre 0 y 1 \u2014 mensajes por debajo del umbral se marcan para revisi\u00f3n manual"
        >
          <TextInput
            value={form.reviewer_confidence_threshold}
            onChange={set("reviewer_confidence_threshold")}
            placeholder="0.7"
            type="number"
          />
        </FieldRow>
      </div>
      <div className="mt-4 flex items-center justify-between">
        {error ? <p className="text-sm text-rose-600">{error}</p> : <span />}
        <SaveButton onClick={save} saving={saving} saved={saved} />
      </div>
    </SectionCard>
  );
}

// ─── Credentials Section (editable DB) ───────────────────────────────

function CredentialsSectionNew({
  data,
  onSaved,
}: {
  data: MailCredentials;
  onSaved: (updated: MailCredentials) => void;
}) {
  const [smtpProvider, setSmtpProvider] = useState<MailProvider>("custom");
  const [imapProvider, setImapProvider] = useState<MailProvider>("custom");

  const [smtpForm, setSmtpForm] = useState({
    smtp_host: data.smtp_host ?? "",
    smtp_port: String(data.smtp_port),
    smtp_username: data.smtp_username ?? "",
    smtp_password: "",
    smtp_ssl: data.smtp_ssl,
    smtp_starttls: data.smtp_starttls,
  });

  const [imapForm, setImapForm] = useState({
    imap_host: data.imap_host ?? "",
    imap_port: String(data.imap_port),
    imap_username: data.imap_username ?? "",
    imap_password: "",
    imap_ssl: data.imap_ssl,
  });

  const [smtpLastTest, setSmtpLastTest] = useState({
    at: data.smtp_last_test_at,
    ok: data.smtp_last_test_ok,
    error: data.smtp_last_test_error,
  });

  const [imapLastTest, setImapLastTest] = useState({
    at: data.imap_last_test_at,
    ok: data.imap_last_test_ok,
    error: data.imap_last_test_error,
  });

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const savedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const setSmtp = (k: string) => (v: string | boolean) =>
    setSmtpForm((prev) => ({ ...prev, [k]: v }));
  const setImap = (k: string) => (v: string | boolean) =>
    setImapForm((prev) => ({ ...prev, [k]: v }));

  const applySmtpPreset = (p: MailProvider) => {
    setSmtpProvider(p);
    const preset = SMTP_PRESETS[p];
    if (preset) {
      setSmtpForm((prev) => ({
        ...prev,
        smtp_host: preset.host,
        smtp_port: String(preset.port),
        smtp_ssl: preset.ssl,
        smtp_starttls: preset.starttls,
      }));
    }
  };

  const applyImapPreset = (p: MailProvider) => {
    setImapProvider(p);
    const preset = IMAP_PRESETS[p];
    if (preset) {
      setImapForm((prev) => ({
        ...prev,
        imap_host: preset.host,
        imap_port: String(preset.port),
        imap_ssl: preset.ssl,
      }));
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await updateMailCredentials({
        smtp_host: smtpForm.smtp_host || null,
        smtp_port: parseInt(smtpForm.smtp_port, 10) || 587,
        smtp_username: smtpForm.smtp_username || null,
        smtp_ssl: smtpForm.smtp_ssl,
        smtp_starttls: smtpForm.smtp_starttls,
        imap_host: imapForm.imap_host || null,
        imap_port: parseInt(imapForm.imap_port, 10) || 993,
        imap_username: imapForm.imap_username || null,
        imap_ssl: imapForm.imap_ssl,
        ...(smtpForm.smtp_password ? { smtp_password: smtpForm.smtp_password } : {}),
        ...(imapForm.imap_password ? { imap_password: imapForm.imap_password } : {}),
      });
      onSaved(updated);
      setSmtpForm((prev) => ({ ...prev, smtp_password: "" }));
      setImapForm((prev) => ({ ...prev, imap_password: "" }));
      setSaved(true);
      if (savedTimer.current) clearTimeout(savedTimer.current);
      savedTimer.current = setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Error al guardar.");
    } finally {
      setSaving(false);
    }
  };

  const handleSmtpTest = async (): Promise<ConnectionTestResult> => {
    const r = await testSmtpConnection();
    setSmtpLastTest({ at: new Date().toISOString(), ok: r.ok, error: r.error });
    return r;
  };

  const handleImapTest = async (): Promise<ConnectionTestResult> => {
    const r = await testImapConnection();
    setImapLastTest({ at: new Date().toISOString(), ok: r.ok, error: r.error });
    return r;
  };

  return (
    <div className="space-y-6">
      <SectionCard
        title="Credenciales SMTP"
        description="Servidor de salida de correo. Las contrase\u00f1as se guardan en DB y nunca se exponen por API."
        icon={KeyRound}
      >
        <div className="mb-5">
          <p className="mb-2 text-xs font-medium text-slate-500">Proveedor</p>
          <ProviderPicker value={smtpProvider} onChange={applySmtpPreset} />
        </div>
        <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
          <div>
            <FieldRow label="Servidor SMTP">
              <TextInput
                value={smtpForm.smtp_host}
                onChange={setSmtp("smtp_host")}
                placeholder="smtp.gmail.com"
              />
            </FieldRow>
            <FieldRow label="Puerto">
              <TextInput
                value={smtpForm.smtp_port}
                onChange={setSmtp("smtp_port")}
                placeholder="587"
                type="number"
              />
            </FieldRow>
            <FieldRow label="SSL/TLS">
              <Toggle
                checked={smtpForm.smtp_ssl}
                onChange={setSmtp("smtp_ssl") as (v: boolean) => void}
                label={smtpForm.smtp_ssl ? "SSL activo" : "Sin SSL"}
              />
            </FieldRow>
            <FieldRow label="STARTTLS">
              <Toggle
                checked={smtpForm.smtp_starttls}
                onChange={setSmtp("smtp_starttls") as (v: boolean) => void}
                label={smtpForm.smtp_starttls ? "STARTTLS activo" : "Sin STARTTLS"}
              />
            </FieldRow>
          </div>
          <div>
            <FieldRow label="Usuario / Email">
              <TextInput
                value={smtpForm.smtp_username}
                onChange={setSmtp("smtp_username")}
                placeholder="vos@gmail.com"
                type="email"
              />
            </FieldRow>
            <FieldRow
              label="Contrase\u00f1a"
              hint="Dejar vac\u00edo para mantener la contrase\u00f1a actual"
            >
              <PasswordInput
                value={smtpForm.smtp_password}
                onChange={setSmtp("smtp_password")}
                alreadySet={data.smtp_password_set}
              />
            </FieldRow>
          </div>
        </div>
        <div className="mt-4 rounded-2xl bg-slate-50 p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="mb-2 text-xs font-medium text-slate-500">
                \u00daltimo test de conexi\u00f3n
              </p>
              <ConnectionTestBadge
                lastAt={smtpLastTest.at}
                lastOk={smtpLastTest.ok}
                lastError={smtpLastTest.error}
              />
            </div>
            <TestButton onTest={handleSmtpTest} label="Probar SMTP" />
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Credenciales IMAP"
        description="Servidor de entrada de correo para sincronizaci\u00f3n de inbox."
        icon={KeyRound}
      >
        <div className="mb-5">
          <p className="mb-2 text-xs font-medium text-slate-500">Proveedor</p>
          <ProviderPicker value={imapProvider} onChange={applyImapPreset} />
        </div>
        <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
          <div>
            <FieldRow label="Servidor IMAP">
              <TextInput
                value={imapForm.imap_host}
                onChange={setImap("imap_host")}
                placeholder="imap.gmail.com"
              />
            </FieldRow>
            <FieldRow label="Puerto">
              <TextInput
                value={imapForm.imap_port}
                onChange={setImap("imap_port")}
                placeholder="993"
                type="number"
              />
            </FieldRow>
            <FieldRow label="SSL/TLS">
              <Toggle
                checked={imapForm.imap_ssl}
                onChange={setImap("imap_ssl") as (v: boolean) => void}
                label={imapForm.imap_ssl ? "SSL activo" : "Sin SSL"}
              />
            </FieldRow>
          </div>
          <div>
            <FieldRow label="Usuario / Email">
              <TextInput
                value={imapForm.imap_username}
                onChange={setImap("imap_username")}
                placeholder="vos@gmail.com"
                type="email"
              />
            </FieldRow>
            <FieldRow
              label="Contrase\u00f1a"
              hint="Dejar vac\u00edo para mantener la contrase\u00f1a actual"
            >
              <PasswordInput
                value={imapForm.imap_password}
                onChange={setImap("imap_password")}
                alreadySet={data.imap_password_set}
              />
            </FieldRow>
          </div>
        </div>
        <div className="mt-4 rounded-2xl bg-slate-50 p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="mb-2 text-xs font-medium text-slate-500">
                \u00daltimo test de conexi\u00f3n
              </p>
              <ConnectionTestBadge
                lastAt={imapLastTest.at}
                lastOk={imapLastTest.ok}
                lastError={imapLastTest.error}
              />
            </div>
            <TestButton onTest={handleImapTest} label="Probar IMAP" />
          </div>
        </div>
      </SectionCard>

      <div className="flex items-center justify-between rounded-2xl border border-slate-100 bg-white p-4">
        {saveError ? (
          <p className="text-sm text-rose-600">{saveError}</p>
        ) : (
          <p className="text-xs text-slate-400">
            Las contrase\u00f1as se guardan de forma segura. Dejar el campo vac\u00edo mantiene la contrase\u00f1a actual.
          </p>
        )}
        <SaveButton onClick={handleSave} saving={saving} saved={saved} />
      </div>
    </div>
  );
}

// ─── Page ──────────────────────────────────────────────────────────────

type TabId =
  | "setup"
  | "brand"
  | "mail_out"
  | "mail_in"
  | "rules"
  | "credentials"
  | "llm";

const TABS: Array<{ id: TabId; label: string }> = [
  { id: "setup", label: "Inicio" },
  { id: "brand", label: "Marca / Firma" },
  { id: "mail_out", label: "Mail de salida" },
  { id: "mail_in", label: "Bandeja de entrada" },
  { id: "rules", label: "Reglas" },
  { id: "credentials", label: "Credenciales" },
  { id: "llm", label: "LLM" },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("setup");
  const [llmData, setLlmData] = useState<LLMSettings | null>(null);
  const [mailData, setMailData] = useState<MailSettings | null>(null);
  const [opData, setOpData] = useState<OperationalSettings | null>(null);
  const [credsData, setCredsData] = useState<MailCredentials | null>(null);
  const [setupData, setSetupData] = useState<SetupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refreshSetup = useCallback(async () => {
    try {
      const s = await getSetupStatus();
      setSetupData(s);
    } catch {
      // non-critical
    }
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(null);

    Promise.allSettled([
      getLLMSettings(),
      getMailSettings(),
      getOperationalSettings(),
      getMailCredentials(),
      getSetupStatus(),
    ]).then(([llm, mail, op, creds, setup]) => {
      if (!active) return;
      if (llm.status === "fulfilled") setLlmData(llm.value);
      if (mail.status === "fulfilled") setMailData(mail.value);
      if (op.status === "fulfilled") setOpData(op.value);
      if (creds.status === "fulfilled") setCredsData(creds.value);
      if (setup.status === "fulfilled") setSetupData(setup.value);
      if (
        llm.status === "rejected" &&
        mail.status === "rejected" &&
        op.status === "rejected"
      ) {
        setLoadError("No se pudo conectar con el backend.");
      }
      setLoading(false);
    });

    return () => {
      active = false;
    };
  }, []);

  const handleSavedOps = (updated: OperationalSettings) => {
    setOpData(updated);
    void refreshSetup();
  };

  const handleSavedCreds = (updated: MailCredentials) => {
    setCredsData(updated);
    void refreshSetup();
  };

  const noData =
    (activeTab === "setup" && !setupData) ||
    (activeTab === "brand" && !opData) ||
    (activeTab === "mail_out" && (!opData || !mailData)) ||
    (activeTab === "mail_in" && (!opData || !mailData)) ||
    (activeTab === "rules" && !opData) ||
    (activeTab === "credentials" && !credsData) ||
    (activeTab === "llm" && !llmData);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Configuraci\u00f3n"
        description="Ajustes operativos del sistema."
      />

      {loading && (
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando configuraci\u00f3n\u2026
        </div>
      )}

      {!loading && loadError && (
        <EmptyState
          icon={Settings}
          title="Sin configuraci\u00f3n disponible"
          description={loadError}
        />
      )}

      {!loading && !loadError && (
        <>
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

          <div>
            {activeTab === "setup" && setupData && (
              <SetupChecklist data={setupData} onTabChange={setActiveTab} />
            )}
            {activeTab === "brand" && opData && (
              <BrandSection data={opData} onSaved={handleSavedOps} />
            )}
            {activeTab === "mail_out" && opData && mailData && (
              <MailOutboundSection
                data={opData}
                mailData={mailData}
                onSaved={handleSavedOps}
              />
            )}
            {activeTab === "mail_in" && opData && mailData && (
              <MailInboundSection
                data={opData}
                mailData={mailData}
                onSaved={handleSavedOps}
              />
            )}
            {activeTab === "rules" && opData && (
              <RulesSection data={opData} onSaved={handleSavedOps} />
            )}
            {activeTab === "credentials" && credsData && (
              <CredentialsSectionNew data={credsData} onSaved={handleSavedCreds} />
            )}
            {activeTab === "llm" && llmData && <LLMSection data={llmData} />}

            {noData && (
              <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
                <div className="flex items-center gap-2">
                  <TriangleAlert className="h-4 w-4 text-amber-500" />
                  No se pudieron cargar los datos para esta secci\u00f3n.
                </div>
              </div>
            )}
          </div>

          {opData?.updated_at && (
            <p className="text-xs text-slate-400">
              \u00daltima actualizaci\u00f3n: <RelativeTime date={opData.updated_at} />
            </p>
          )}
        </>
      )}
    </div>
  );
}
