"use client";

import { useCallback, useState } from "react";
import {
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  RefreshCw,
  Save,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
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
  action,
  className,
  children,
}: {
  title: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  action?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className={cn(
        "rounded-2xl border border-border bg-card p-5",
        className
      )}
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          {Icon && (
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted text-foreground">
              <Icon className="h-4 w-4" />
            </div>
          )}
          <div className="min-w-0">
            <h2 className="font-heading text-base font-semibold text-foreground">{title}</h2>
            {description && (
              <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
            )}
          </div>
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      {children}
    </section>
  );
}

// ─── SectionSubheading (Panel-style uppercase label) ─────────────────

export function SectionSubheading({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "text-[10px] font-semibold uppercase tracking-wider text-muted-foreground",
        className
      )}
    >
      {children}
    </p>
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
    positive: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300",
    warning: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
    neutral: "bg-muted text-muted-foreground",
    danger: "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        styles[tone]
      )}
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
    <div className="flex flex-col gap-1.5 py-2.5 first:pt-0 last:pb-0">
      <label className="text-xs font-medium text-foreground/80">{label}</label>
      {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
      {children}
    </div>
  );
}

// ─── TextInput ───────────────────────────────────────────────────────

const inputClasses =
  "w-full rounded-lg border border-border bg-muted/40 dark:bg-input/30 px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:bg-card focus:ring-3 focus:ring-ring/30 disabled:opacity-50";

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
      className={inputClasses}
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
            ? "••••••••"
            : (placeholder ?? "Nueva contraseña")
        }
        className={cn(inputClasses, "pr-20")}
      />
      <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
        {alreadySet && isEmpty && (
          <Lock className="h-3.5 w-3.5 text-emerald-500" />
        )}
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
          tabIndex={-1}
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

// ─── Select (styled <select> to match TextInput) ─────────────────────

export function Select({
  value,
  onChange,
  disabled,
  children,
}: {
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className={cn(inputClasses, "appearance-none pr-8")}
    >
      {children}
    </select>
  );
}

// ─── ToggleListItem (Panel-style toggle row) ────────────────────────

export function ToggleListItem({
  label,
  hint,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={cn(
        "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors disabled:opacity-40",
        checked
          ? "bg-emerald-50 dark:bg-emerald-950/30"
          : "bg-muted/30 hover:bg-muted/50"
      )}
    >
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-foreground">{label}</p>
        {hint && (
          <p className="truncate text-[10px] text-muted-foreground">{hint}</p>
        )}
      </div>
      <div
        className={cn(
          "flex h-5 w-9 flex-shrink-0 items-center rounded-full px-0.5 transition-colors",
          checked ? "bg-emerald-600" : "bg-muted-foreground/30"
        )}
      >
        <div
          className={cn(
            "h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
            checked ? "translate-x-4" : "translate-x-0"
          )}
        />
      </div>
    </button>
  );
}

// ─── Toggle (slide switch, matches FeatureToggleList) ───────────────

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
      className={cn(
        "inline-flex items-center gap-2.5 text-sm transition-opacity",
        disabled && "cursor-not-allowed opacity-40"
      )}
    >
      <div
        className={cn(
          "flex h-5 w-9 flex-shrink-0 items-center rounded-full px-0.5 transition-colors",
          checked ? "bg-emerald-600" : "bg-muted-foreground/30"
        )}
      >
        <div
          className={cn(
            "h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
            checked ? "translate-x-4" : "translate-x-0"
          )}
        />
      </div>
      {label && (
        <span
          className={cn(
            "text-xs",
            checked ? "text-foreground" : "text-muted-foreground"
          )}
        >
          {label}
        </span>
      )}
    </button>
  );
}

// ─── SaveButton ──────────────────────────────────────────────────────

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
      className="inline-flex items-center gap-2 rounded-lg bg-foreground px-3.5 py-2 text-xs font-medium text-background transition hover:bg-foreground/80 active:translate-y-px disabled:opacity-50"
    >
      {saving ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Save className="h-3.5 w-3.5" />
      )}
      {saving ? "Guardando…" : "Guardar"}
    </button>
  );
}

// ─── SectionFooter ───────────────────────────────────────────────────

export function SectionFooter({
  updatedAt,
  onSave,
  saving,
  disabled,
}: {
  updatedAt: string | null;
  onSave: () => void;
  saving: boolean;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-t border-border/60 pt-4">
      <p className="text-[11px] text-muted-foreground">
        {updatedAt ? (
          <>
            Última actualización ·{" "}
            <RelativeTime date={updatedAt} className="text-foreground/70" />
          </>
        ) : (
          "Sin cambios guardados"
        )}
      </p>
      <SaveButton onClick={onSave} saving={saving} disabled={disabled} />
    </div>
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
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => (
        <button
          key={opt.id}
          type="button"
          onClick={() => onChange(opt.id)}
          className={cn(
            "rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors",
            value === opt.id
              ? "border-foreground bg-foreground text-background"
              : "border-border bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
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
          className={cn(
            "text-xs font-medium",
            lastOk
              ? "text-emerald-700 dark:text-emerald-300"
              : "text-rose-700 dark:text-rose-300"
          )}
        >
          {lastOk ? "Conexión exitosa" : "Falló"}
        </span>
        <span className="text-xs text-muted-foreground">
          &middot; <RelativeTime date={lastAt} />
        </span>
      </div>
      {!lastOk && lastError && (
        <p className="rounded-md bg-rose-50 px-2 py-1 text-[11px] text-rose-600 dark:bg-rose-950/30 dark:text-rose-300">
          {lastError}
        </p>
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
    } catch (err) {
      console.error("connection_test_failed", err);
      setResult({ ok: false, error: "Error de red al probar conexión.", sample_count: null });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        type="button"
        onClick={run}
        disabled={testing}
        className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted active:translate-y-px disabled:opacity-50"
      >
        {testing ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <RefreshCw className="h-3.5 w-3.5" />
        )}
        {testing ? "Probando…" : label}
      </button>
      {result && (
        <div
          className={cn(
            "flex items-center gap-1.5 text-[11px] font-medium",
            result.ok
              ? "text-emerald-700 dark:text-emerald-300"
              : "text-rose-700 dark:text-rose-300"
          )}
        >
          {result.ok ? (
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
          ) : (
            <XCircle className="h-3.5 w-3.5 text-rose-500" />
          )}
          {result.ok
            ? `OK${result.sample_count != null ? ` · ${result.sample_count} msgs` : ""}`
            : result.error}
        </div>
      )}
    </div>
  );
}
