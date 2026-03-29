"use client";

import { useCallback, useRef, useState } from "react";
import {
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  RefreshCw,
  Save,
  ToggleLeft,
  ToggleRight,
  XCircle,
} from "lucide-react";
import { RelativeTime } from "@/components/shared/relative-time";
import { updateOperationalSettings } from "@/lib/api/client";
import { sileo } from "sileo";
import type { ConnectionTestResult, OperationalSettings } from "@/types";
import type { MailProvider } from "./mail-presets";

// ─── SectionCard ─────────────────────────────────────────────────────

export function SettingsSectionCard({
  title,
  description,
  icon: Icon,
  children,
}: {
  title: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="mb-5 flex items-start gap-3">
        {Icon && (
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white">
            <Icon className="h-4 w-4" />
          </div>
        )}
        <div>
          <h2 className="font-heading text-base font-semibold text-foreground">{title}</h2>
          {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

// ─── MetaRow ─────────────────────────────────────────────────────────

export function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-3 last:border-b-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="text-right text-sm font-medium text-foreground">{value}</div>
    </div>
  );
}

// ─── StatusPill ──────────────────────────────────────────────────────

export function StatusPill({
  label,
  tone,
}: {
  label: string;
  tone: "positive" | "warning" | "neutral" | "danger";
}) {
  const styles = {
    positive: "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700",
    warning: "bg-amber-50 dark:bg-amber-950/30 text-amber-700",
    neutral: "bg-muted text-muted-foreground",
    danger: "bg-rose-50 dark:bg-rose-950/30 text-rose-700",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${styles[tone]}`}
    >
      {label}
    </span>
  );
}

// ─── FieldRow ────────────────────────────────────────────────────────

export function FieldRow({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5 border-b border-border py-3 last:border-b-0">
      <label className="text-sm font-medium text-foreground/80">{label}</label>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      {children}
    </div>
  );
}

// ─── TextInput ───────────────────────────────────────────────────────

export function TextInput({
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
      className="w-full rounded-xl border border-border bg-muted px-3 py-2 text-sm text-foreground outline-none transition focus:border-border focus:bg-card disabled:opacity-50"
    />
  );
}

// ─── PasswordInput ───────────────────────────────────────────────────

export function PasswordInput({
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
            ? "••••••••  (ya configurado)"
            : (placeholder ?? "Nueva contraseña")
        }
        className="w-full rounded-xl border border-border bg-muted px-3 py-2 pr-20 text-sm text-foreground outline-none transition focus:border-border focus:bg-card"
      />
      <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
        {alreadySet && isEmpty && (
          <Lock className="h-3.5 w-3.5 text-emerald-500" />
        )}
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="rounded p-1 text-muted-foreground hover:text-muted-foreground"
          tabIndex={-1}
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

// ─── Toggle ──────────────────────────────────────────────────────────

export function Toggle({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label?: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={`flex items-center gap-2 text-sm ${disabled ? "opacity-40 cursor-not-allowed text-muted-foreground" : "text-foreground/80"}`}
    >
      {checked ? (
        <ToggleRight className="h-5 w-5 text-emerald-600" />
      ) : (
        <ToggleLeft className="h-5 w-5 text-muted-foreground" />
      )}
      {label && <span>{label}</span>}
    </button>
  );
}

// ─── SaveButton (simplified: no saved/error state — toast handles it) ─

export function SaveButton({
  onClick,
  saving,
  disabled,
}: {
  onClick: () => void;
  saving: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={saving || disabled}
      className="flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-700 disabled:opacity-50"
    >
      {saving ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Save className="h-4 w-4" />
      )}
      {saving ? "Guardando…" : "Guardar"}
    </button>
  );
}

// ─── useSave (wraps updateOperationalSettings with sileo.promise) ────

export function useSave(
  getData: () => Partial<OperationalSettings>,
  onSaved: (updated: OperationalSettings) => void
) {
  const [saving, setSaving] = useState(false);

  const save = useCallback(async () => {
    setSaving(true);
    try {
      const updated = await sileo.promise(
        updateOperationalSettings(getData()),
        {
          loading: { title: "Guardando configuración…" },
          success: { title: "Configuración guardada" },
          error: (err: unknown) => ({
            title: "Error al guardar",
            description: err instanceof Error ? err.message : "Error desconocido.",
          }),
        }
      );
      onSaved(updated);
    } finally {
      setSaving(false);
    }
  }, [getData, onSaved]);

  return { save, saving };
}

// ─── ProviderPicker ──────────────────────────────────────────────────

export function ProviderPicker({
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
              ? "border-violet-700 bg-violet-600 text-white"
              : "border-border bg-card text-muted-foreground hover:border-border"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

// ─── ConnectionTestBadge ─────────────────────────────────────────────

export function ConnectionTestBadge({
  lastAt,
  lastOk,
  lastError,
}: {
  lastAt: string | null;
  lastOk: boolean | null;
  lastError: string | null;
}) {
  if (!lastAt) {
    return <span className="text-xs text-muted-foreground">Sin prueba realizada</span>;
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
          {lastOk ? "Conexión exitosa" : "Falló"}
        </span>
        <span className="text-xs text-muted-foreground">
          &middot; <RelativeTime date={lastAt} />
        </span>
      </div>
      {!lastOk && lastError && (
        <p className="rounded-lg bg-rose-50 dark:bg-rose-950/30 px-2 py-1 text-xs text-rose-600">{lastError}</p>
      )}
    </div>
  );
}

// ─── TestButton (wraps test call with sileo.promise) ─────────────────

export function TestButton({
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
      const r = await sileo.promise(onTest(), {
        loading: { title: `Probando ${label.toLowerCase()}…` },
        success: (data: ConnectionTestResult) => ({
          title: data.ok
            ? `${label}: conexión exitosa`
            : `${label}: falló`,
        }),
        error: { title: "Error de red al probar conexión" },
      });
      setResult(r);
    } catch {
      setResult({ ok: false, error: "Error de red al probar conexión.", sample_count: null });
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
        className="flex w-fit items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium text-foreground/80 transition hover:border-border disabled:opacity-50"
      >
        {testing ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        {testing ? "Probando…" : label}
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
            ? `Conexión OK${result.sample_count != null ? ` · ${result.sample_count} mensajes encontrados` : ""}`
            : result.error}
        </div>
      )}
    </div>
  );
}
