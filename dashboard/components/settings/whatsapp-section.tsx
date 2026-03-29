"use client";

import { useState, useEffect } from "react";
import { MessageCircle, Shield, Zap, Terminal, Copy, Check } from "lucide-react";
import { sileo } from "sileo";
import {
  SettingsSectionCard,
  FieldRow,
  TextInput,
  PasswordInput,
  SaveButton,
  Toggle,
  ConnectionTestBadge,
  TestButton,
} from "./settings-primitives";
import type { ConnectionTestResult } from "@/types";
import type { OperationalSettings, LLMSettings } from "@/types";
import { API_BASE_URL } from "@/lib/constants";
import { getLLMSettings } from "@/lib/api/client";

// ─── Types ───────────────────────────────────────────────────────────

export interface WhatsAppCredentials {
  provider: string;
  phone_number: string | null;
  api_key_set: boolean;
  webhook_secret_set: boolean;
  webhook_url: string | null;
  last_test_at: string | null;
  last_test_ok: boolean | null;
  last_test_error: string | null;
  updated_at: string | null;
}

// ─── API helpers ─────────────────────────────────────────────────────

async function updateWhatsAppCredentials(
  updates: { phone_number?: string | null; api_key?: string }
): Promise<WhatsAppCredentials> {
  const res = await fetch(`${API_BASE_URL}/settings/whatsapp-credentials`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

async function testWhatsAppConnection(): Promise<ConnectionTestResult> {
  const res = await fetch(`${API_BASE_URL}/settings/test/whatsapp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

// ─── WhatsApp Credentials (CallMeBot alertas) ────────────────────────

interface WhatsAppSectionProps {
  data: WhatsAppCredentials;
  onSaved: (updated: WhatsAppCredentials) => void;
}

export function WhatsAppSection({ data, onSaved }: WhatsAppSectionProps) {
  const [form, setForm] = useState({
    phone_number: data.phone_number ?? "",
    api_key: "",
  });

  const [lastTest, setLastTest] = useState({
    at: data.last_test_at,
    ok: data.last_test_ok,
    error: data.last_test_error,
  });

  const [saving, setSaving] = useState(false);

  const set = (k: string) => (v: string | boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await sileo.promise(
        updateWhatsAppCredentials({
          phone_number: form.phone_number || null,
          ...(form.api_key ? { api_key: form.api_key } : {}),
        }),
        {
          loading: { title: "Guardando credenciales WhatsApp..." },
          success: { title: "Credenciales WhatsApp guardadas" },
          error: (err: unknown) => ({
            title: "Error al guardar credenciales WhatsApp",
            description: err instanceof Error ? err.message : "Error desconocido.",
          }),
        }
      );
      onSaved(updated);
      setForm((prev) => ({ ...prev, api_key: "" }));
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (): Promise<ConnectionTestResult> => {
    const r = await testWhatsAppConnection();
    setLastTest({ at: new Date().toISOString(), ok: r.ok, error: r.error });
    return r;
  };

  return (
    <div className="space-y-6">
      <SettingsSectionCard
        title="Credenciales WhatsApp"
        description="Configuracion del proveedor de mensajeria WhatsApp para alertas y notificaciones."
        icon={MessageCircle}
      >
        <div className="mb-5">
          <p className="mb-2 text-xs font-medium text-muted-foreground">Proveedor</p>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-xl border border-slate-900 bg-foreground px-4 py-2 text-sm font-medium text-white">
              {data.provider || "CallMeBot"}
            </span>
          </div>
        </div>

        <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
          <div>
            <FieldRow label="Numero de telefono" hint="Formato internacional, ej: +5491112345678">
              <TextInput
                value={form.phone_number}
                onChange={set("phone_number")}
                placeholder="+5491112345678"
              />
            </FieldRow>
          </div>
          <div>
            <FieldRow
              label="API Key"
              hint="Dejar vacio para mantener la clave actual"
            >
              <PasswordInput
                value={form.api_key}
                onChange={set("api_key")}
                alreadySet={data.api_key_set}
                placeholder="API key de CallMeBot"
              />
            </FieldRow>
            <FieldRow label="Estado de la API key">
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
                    data.api_key_set
                      ? "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700"
                      : "bg-amber-50 dark:bg-amber-950/30 text-amber-700"
                  }`}
                >
                  {data.api_key_set ? "Configurada" : "No configurada"}
                </span>
              </div>
            </FieldRow>
          </div>
        </div>

        <div className="mt-4 rounded-2xl bg-muted p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="mb-2 text-xs font-medium text-muted-foreground">
                Ultimo test de conexion
              </p>
              <ConnectionTestBadge
                lastAt={lastTest.at}
                lastOk={lastTest.ok}
                lastError={lastTest.error}
              />
            </div>
            <TestButton onTest={handleTest} label="Probar WhatsApp" />
          </div>
        </div>
      </SettingsSectionCard>

      <div className="flex items-center justify-between rounded-2xl border border-border bg-card p-4">
        <p className="text-xs text-muted-foreground">
          La API key se guarda de forma segura. Dejar el campo vacio mantiene la clave actual.
        </p>
        <SaveButton onClick={handleSave} saving={saving} />
      </div>
    </div>
  );
}

// ─── OpenClaw por WhatsApp ───────────────────────────────────────────

const MODEL_ROLE_OPTIONS = [
  { value: "leader", label: "Leader (rapido, 4b)", hint: "Respuestas rapidas, menor calidad" },
  { value: "executor", label: "Executor (balanceado, 9b)", hint: "Balance entre velocidad y calidad" },
  { value: "reviewer", label: "Reviewer (preciso, 27b)", hint: "Mejor calidad, mas lento y pesado" },
];

interface OpenClawWhatsAppProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
  waCredsData?: WhatsAppCredentials | null;
  onWaCredsSaved?: (updated: WhatsAppCredentials) => void;
}

export function OpenClawWhatsAppSection({ data, onSaved }: OpenClawWhatsAppProps) {
  const [form, setForm] = useState({
    whatsapp_conversational_enabled: data.whatsapp_conversational_enabled ?? false,
    whatsapp_openclaw_enrichment: data.whatsapp_openclaw_enrichment ?? false,
    whatsapp_actions_enabled: data.whatsapp_actions_enabled ?? false,
    openclaw_model: data.openclaw_model ?? "leader",
    openclaw_max_response_chars: data.openclaw_max_response_chars ?? 600,
    openclaw_rate_limit: data.openclaw_rate_limit ?? 20,
    openclaw_rate_window_seconds: data.openclaw_rate_window_seconds ?? 900,
  });

  const [saving, setSaving] = useState(false);
  const [llmInfo, setLlmInfo] = useState<LLMSettings | null>(null);

  useEffect(() => {
    getLLMSettings().then(setLlmInfo).catch(() => {});
  }, []);

  const toggle = (k: string) => (v: boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const setField = (k: string) => (v: string | number) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/settings/operational`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const updated = await res.json();
      sileo.success({ title: "Configuracion de OpenClaw actualizada" });
      onSaved(updated);
    } catch (err) {
      sileo.error({
        title: "Error al guardar",
        description: err instanceof Error ? err.message : "Error desconocido.",
      });
    } finally {
      setSaving(false);
    }
  };

  const modelInfo = MODEL_ROLE_OPTIONS.find((m) => m.value === form.openclaw_model);
  const actualModel = llmInfo
    ? form.openclaw_model === "leader"
      ? llmInfo.leader_model
      : form.openclaw_model === "reviewer"
        ? llmInfo.reviewer_model
        : llmInfo.executor_model
    : null;

  return (
    <SettingsSectionCard
      title="OpenClaw por WhatsApp"
      description="Conecta OpenClaw a WhatsApp para chatear con tu IA, consultar datos del sistema y ejecutar acciones por mensaje."
      icon={MessageCircle}
    >
      <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
        {/* ── Left: Feature toggles + configuration ── */}
        <div>
          <FieldRow
            label="WhatsApp conversacional"
            hint="Recibir y responder mensajes por WhatsApp (comandos: leads, stats, etc)"
          >
            <Toggle
              checked={form.whatsapp_conversational_enabled}
              onChange={toggle("whatsapp_conversational_enabled")}
              label={form.whatsapp_conversational_enabled ? "Activo" : "Inactivo"}
            />
          </FieldRow>
          <FieldRow
            label="OpenClaw IA"
            hint="Mensajes que no son comandos los responde la IA con contexto del sistema"
          >
            <Toggle
              checked={form.whatsapp_openclaw_enrichment}
              onChange={toggle("whatsapp_openclaw_enrichment")}
              label={form.whatsapp_openclaw_enrichment ? "Activo" : "Inactivo"}
              disabled={!form.whatsapp_conversational_enabled}
            />
          </FieldRow>
          <FieldRow
            label="Acciones por WhatsApp"
            hint="Aprobar drafts, resolver notificaciones via WhatsApp con confirmacion"
          >
            <Toggle
              checked={form.whatsapp_actions_enabled}
              onChange={toggle("whatsapp_actions_enabled")}
              label={form.whatsapp_actions_enabled ? "Activo" : "Inactivo"}
              disabled={!form.whatsapp_conversational_enabled}
            />
          </FieldRow>

          <div className="mt-2 border-t border-border pt-4">
            <FieldRow
              label="Modelo de IA"
              hint={modelInfo?.hint ?? "Modelo que usa OpenClaw para responder"}
            >
              <select
                value={form.openclaw_model}
                onChange={(e) => setField("openclaw_model")(e.target.value)}
                disabled={!form.whatsapp_openclaw_enrichment}
                className="w-full rounded-xl border border-border bg-muted px-3 py-2 text-sm text-foreground outline-none transition focus:border-border focus:bg-card disabled:opacity-50"
              >
                {MODEL_ROLE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              {actualModel && (
                <p className="mt-1 text-[10px] text-muted-foreground/60">
                  Modelo actual: {actualModel}
                </p>
              )}
            </FieldRow>
            <FieldRow
              label="Largo maximo de respuesta"
              hint="Caracteres maximos por respuesta de OpenClaw"
            >
              <input
                type="number"
                min={100}
                max={2000}
                step={50}
                value={form.openclaw_max_response_chars}
                onChange={(e) => setField("openclaw_max_response_chars")(Number(e.target.value))}
                disabled={!form.whatsapp_openclaw_enrichment}
                className="w-full rounded-xl border border-border bg-muted px-3 py-2 text-sm text-foreground outline-none transition focus:border-border focus:bg-card disabled:opacity-50"
              />
            </FieldRow>
          </div>
        </div>

        {/* ── Right: Security, rate limiting, setup guide ── */}
        <div className="space-y-4">
          {/* Security */}
          <div className="rounded-xl border border-border bg-card p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <p className="font-medium text-sm text-foreground">Seguridad</p>
            </div>
            <div className="space-y-2">
              <SecurityRow label="Proteccion SQL injection" ok detail="Patron regex activo" />
              <SecurityRow label="Sanitizado HTML/XSS" ok detail="Tags HTML removidos automaticamente" />
              <SecurityRow label="Truncado de input" ok detail="Maximo 500 caracteres por mensaje" />
              <SecurityRow
                label="Truncado de respuesta"
                ok
                detail={`Maximo ${form.openclaw_max_response_chars} caracteres`}
              />
              <SecurityRow
                label="Confirmacion de acciones"
                ok={form.whatsapp_actions_enabled}
                detail={form.whatsapp_actions_enabled ? "Acciones requieren confirmacion explicita" : "Acciones deshabilitadas"}
              />
            </div>
          </div>

          {/* Rate limiting */}
          <div className="rounded-xl border border-border bg-card p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <p className="font-medium text-sm text-foreground">Rate limiting</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-medium text-muted-foreground">
                  Mensajes maximos
                </label>
                <input
                  type="number"
                  min={5}
                  max={100}
                  value={form.openclaw_rate_limit}
                  onChange={(e) => setField("openclaw_rate_limit")(Number(e.target.value))}
                  className="mt-1 w-full rounded-xl border border-border bg-muted px-3 py-2 text-sm text-foreground outline-none transition focus:border-border focus:bg-card"
                />
              </div>
              <div>
                <label className="text-[11px] font-medium text-muted-foreground">
                  Ventana (segundos)
                </label>
                <input
                  type="number"
                  min={60}
                  max={3600}
                  step={60}
                  value={form.openclaw_rate_window_seconds}
                  onChange={(e) => setField("openclaw_rate_window_seconds")(Number(e.target.value))}
                  className="mt-1 w-full rounded-xl border border-border bg-muted px-3 py-2 text-sm text-foreground outline-none transition focus:border-border focus:bg-card"
                />
              </div>
            </div>
            <p className="text-[10px] text-muted-foreground/60">
              {form.openclaw_rate_limit} mensajes cada {Math.round(form.openclaw_rate_window_seconds / 60)} minutos por telefono
            </p>
          </div>

          {/* Setup guide */}
          <OpenClawSetupGuide />
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <SaveButton onClick={handleSave} saving={saving} />
      </div>
    </SettingsSectionCard>
  );
}

// ─── Kapso WhatsApp Outreach ────────────────────────────────────────

interface KapsoOutreachSectionProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function KapsoOutreachSection({ data, onSaved }: KapsoOutreachSectionProps) {
  const [enabled, setEnabled] = useState(data.whatsapp_outreach_enabled ?? false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null);

  const handleToggle = async (value: boolean) => {
    setEnabled(value);
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/settings/operational`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ whatsapp_outreach_enabled: value }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const updated = await res.json();
      sileo.success({
        title: value
          ? "Outreach por WhatsApp activado"
          : "Outreach por WhatsApp desactivado",
      });
      onSaved(updated);
    } catch (err) {
      setEnabled(!value);
      sileo.error({
        title: "Error al guardar",
        description: err instanceof Error ? err.message : "Error desconocido.",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/settings/test/kapso`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
      const result = await res.json();
      setTestResult(result);
      if (result.status === "ok") {
        sileo.success({ title: "Kapso: conexion exitosa" });
      } else {
        sileo.error({ title: "Kapso: fallo la conexion", description: result.message });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error de red";
      setTestResult({ status: "error", message: msg });
      sileo.error({ title: "Error al testear Kapso", description: msg });
    } finally {
      setTesting(false);
    }
  };

  return (
    <SettingsSectionCard
      title="WhatsApp Outreach (Kapso)"
      description="Genera y envia borradores de outreach por WhatsApp usando la API de Kapso."
      icon={MessageCircle}
    >
      <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
        {/* Left: toggle + status */}
        <div>
          <FieldRow
            label="Outreach por WhatsApp"
            hint="Habilita la generacion de drafts de outreach para el canal WhatsApp"
          >
            <Toggle
              checked={enabled}
              onChange={handleToggle}
              label={enabled ? "Activo" : "Inactivo"}
              disabled={saving}
            />
          </FieldRow>
        </div>

        {/* Right: connection test */}
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <p className="font-medium text-sm text-foreground">Conexion Kapso</p>
            </div>

            <div className="flex items-start justify-between gap-4">
              <div>
                {testResult ? (
                  <div className="flex items-center gap-1.5">
                    {testResult.status === "ok" ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-rose-500" />
                    )}
                    <span
                      className={`text-xs font-medium ${
                        testResult.status === "ok" ? "text-emerald-700" : "text-rose-700"
                      }`}
                    >
                      {testResult.message}
                    </span>
                  </div>
                ) : (
                  <span className="text-xs text-muted-foreground">Sin prueba realizada</span>
                )}
              </div>
              <button
                type="button"
                onClick={handleTest}
                disabled={testing}
                className="flex w-fit items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium text-foreground/80 transition hover:border-border disabled:opacity-50"
              >
                {testing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Wifi className="h-4 w-4" />
                )}
                Testear conexion
              </button>
            </div>
          </div>

          <p className="text-[10px] text-muted-foreground/60">
            La API key de Kapso se configura en el archivo .env del servidor
          </p>
        </div>
      </div>
    </SettingsSectionCard>
  );
}

// ─── Security indicator row ──────────────────────────────────────────

function SecurityRow({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  return (
    <div className="flex items-start gap-2.5">
      <span
        className={`mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full ${
          ok
            ? "bg-emerald-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]"
            : "bg-amber-500 shadow-[0_0_6px_rgba(234,179,8,0.5)]"
        }`}
      />
      <div className="min-w-0">
        <p className="text-xs font-medium text-foreground">{label}</p>
        <p className="text-[10px] text-muted-foreground truncate">{detail}</p>
      </div>
    </div>
  );
}

// ─── OpenClaw Automated Setup ────────────────────────────────────────

import { Loader2, CheckCircle2, XCircle, Wifi, QrCode, Play } from "lucide-react";

interface OpenClawStatus {
  installed: boolean;
  version: string | null;
  config_exists: boolean;
  whatsapp_configured: boolean;
  whatsapp_linked: boolean;
  gateway_running: boolean;
  allowed_numbers: string[];
}

function OpenClawSetupGuide() {
  const [status, setStatus] = useState<OpenClawStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [phoneInput, setPhoneInput] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/settings/openclaw/status`);
      if (res.ok) setStatus(await res.json());
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { fetchStatus(); }, []);

  const runAction = async (endpoint: string, body?: object, actionKey?: string) => {
    const key = actionKey ?? endpoint;
    setActionLoading(key);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE_URL}/settings/openclaw/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage({ text: data.message, ok: true });
        sileo.success({ title: data.message });
        await fetchStatus();
      } else {
        setMessage({ text: data.detail ?? "Error desconocido", ok: false });
        sileo.error({ title: data.detail ?? "Error" });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error de conexion";
      setMessage({ text: msg, ok: false });
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Verificando OpenClaw...
      </div>
    );
  }

  if (!status || !status.installed) {
    return (
      <div className="rounded-xl border border-border bg-card p-4 space-y-2">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-amber-500" />
          <p className="text-xs font-semibold text-foreground">OpenClaw no detectado</p>
        </div>
        <p className="text-[10px] text-muted-foreground">
          Instala OpenClaw en WSL para conectar WhatsApp:
        </p>
        <code className="block rounded-lg bg-muted/70 px-3 py-2 text-[11px] font-mono text-violet-400 dark:text-violet-300 select-all">
          npm install -g openclaw@latest
        </code>
        <button onClick={fetchStatus} className="text-[10px] text-violet-500 hover:text-violet-400 font-medium">
          Verificar de nuevo
        </button>
      </div>
    );
  }

  const allDone = status.whatsapp_configured && status.whatsapp_linked && status.gateway_running;

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="h-3.5 w-3.5 text-violet-500" />
          <span className="text-xs font-semibold text-foreground">OpenClaw WhatsApp</span>
        </div>
        <span className={`text-[10px] font-medium ${allDone ? "text-emerald-500" : "text-amber-500"}`}>
          {allDone ? "Conectado" : "Configurar"}
        </span>
      </div>

      <div className="border-t border-border px-4 py-3 space-y-3">
        {/* Status indicators */}
        <div className="grid grid-cols-2 gap-2">
          <StatusDot ok={status.installed} label={`Instalado ${status.version ?? ""}`} />
          <StatusDot ok={status.config_exists} label="Config encontrada" />
          <StatusDot ok={status.whatsapp_configured} label="WhatsApp configurado" />
          <StatusDot ok={status.whatsapp_linked} label="WhatsApp vinculado" />
          <StatusDot ok={status.gateway_running} label="Gateway activo" />
          {status.allowed_numbers.length > 0 && (
            <StatusDot ok label={status.allowed_numbers.join(", ")} />
          )}
        </div>

        {/* Step 1: Configure WhatsApp (if not configured) */}
        {!status.whatsapp_configured && (
          <div className="rounded-lg border border-violet-500/20 bg-violet-50 dark:bg-violet-950/20 p-3 space-y-2">
            <p className="text-[10px] font-semibold text-violet-700 dark:text-violet-300">
              Paso 1: Configurar WhatsApp
            </p>
            <p className="text-[10px] text-violet-600 dark:text-violet-400/80">
              Ingresa tu numero de WhatsApp para agregar el canal a OpenClaw:
            </p>
            <div className="flex items-center gap-2">
              <TextInput
                value={phoneInput}
                onChange={(v) => setPhoneInput(v as string)}
                placeholder="+5491112345678"
              />
              <button
                onClick={() => runAction("setup-whatsapp", { phone_number: phoneInput }, "setup")}
                disabled={!phoneInput.trim() || actionLoading === "setup"}
                className="flex shrink-0 items-center gap-1.5 rounded-xl bg-violet-600 px-3 py-2 text-[11px] font-semibold text-white hover:bg-violet-700 transition-colors disabled:opacity-40"
              >
                {actionLoading === "setup" ? <Loader2 className="h-3 w-3 animate-spin" /> : <MessageCircle className="h-3 w-3" />}
                Configurar
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Link WhatsApp (if configured but not linked) */}
        {status.whatsapp_configured && !status.whatsapp_linked && (
          <WhatsAppLinkStep onLinked={fetchStatus} />
        )}

        {/* Step 3: Start gateway (if linked but not running) */}
        {status.whatsapp_linked && !status.gateway_running && (
          <div className="rounded-lg border border-emerald-500/20 bg-emerald-50 dark:bg-emerald-950/20 p-3 space-y-2">
            <p className="text-[10px] font-semibold text-emerald-700 dark:text-emerald-300">
              Paso 3: Iniciar gateway
            </p>
            <p className="text-[10px] text-emerald-600 dark:text-emerald-400/80">
              WhatsApp esta vinculado. Inicia el gateway para empezar a recibir y responder mensajes.
            </p>
            <button
              onClick={() => runAction("start-gateway", undefined, "gateway")}
              disabled={actionLoading === "gateway"}
              className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-[11px] font-semibold text-white hover:bg-emerald-700 transition-colors disabled:opacity-50"
            >
              {actionLoading === "gateway" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              Iniciar gateway
            </button>
          </div>
        )}

        {/* All done */}
        {allDone && (
          <div className="rounded-lg bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-500/20 p-3">
            <p className="text-[10px] text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5">
              <Wifi className="h-3.5 w-3.5" />
              <span className="font-semibold">OpenClaw esta conectado a WhatsApp.</span>{" "}
              Mandate un mensaje y la IA responde.
            </p>
          </div>
        )}

        {/* Message feedback */}
        {message && (
          <p className={`text-[10px] flex items-center gap-1 ${message.ok ? "text-emerald-600" : "text-red-500"}`}>
            {message.ok ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
            {message.text}
          </p>
        )}

        {/* Refresh — inline text link, not a floating button */}
        <div className="flex justify-end">
          <button
            onClick={fetchStatus}
            className="text-[10px] text-muted-foreground hover:text-foreground font-medium transition-colors"
          >
            Actualizar estado
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── WhatsApp Link Step (opens terminal for QR scan) ─────────────────

function WhatsAppLinkStep({ onLinked }: { onLinked: () => void }) {
  const [phase, setPhase] = useState<"idle" | "opening" | "waiting">("idle");
  const [fallbackCmd, setFallbackCmd] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Poll for linked status while waiting
  useEffect(() => {
    if (phase !== "waiting") return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/settings/openclaw/status`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.whatsapp_linked) {
          clearInterval(interval);
          setPhase("idle");
          sileo.success({ title: "WhatsApp vinculado correctamente" });
          onLinked();
        }
      } catch { /* ignore */ }
    }, 3000);

    return () => clearInterval(interval);
  }, [phase, onLinked]);

  const openTerminal = async () => {
    setPhase("opening");
    setError(null);
    setFallbackCmd(null);
    try {
      const res = await fetch(`${API_BASE_URL}/settings/openclaw/link-whatsapp`, {
        method: "POST",
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail ?? "Error al abrir terminal");
        setPhase("idle");
        return;
      }
      if (data.method === "manual") {
        // Couldn't open terminal — show command to copy
        setFallbackCmd(data.command);
        setPhase("waiting");
      } else {
        // Terminal opened successfully
        setPhase("waiting");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error de conexion");
      setPhase("idle");
    }
  };

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-lg border border-blue-500/20 bg-blue-50 dark:bg-blue-950/20 p-3 space-y-2">
      <div className="flex items-center gap-2">
        <QrCode className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
        <p className="text-[10px] font-semibold text-blue-700 dark:text-blue-300">
          Paso 2: Vincular WhatsApp
        </p>
      </div>
      <p className="text-[10px] text-blue-600 dark:text-blue-400/80">
        Se abre una terminal con el QR. Escanealo desde WhatsApp &gt; Dispositivos vinculados.
      </p>

      {phase === "idle" && (
        <button
          onClick={openTerminal}
          className="flex items-center gap-1.5 rounded-xl bg-blue-600 px-3 py-2 text-[11px] font-semibold text-white hover:bg-blue-700 transition-colors"
        >
          <Terminal className="h-3 w-3" />
          Abrir terminal con QR
        </button>
      )}

      {phase === "opening" && (
        <div className="flex items-center gap-2 text-[10px] text-blue-600 dark:text-blue-400">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Abriendo terminal...
        </div>
      )}

      {phase === "waiting" && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 rounded-lg bg-blue-100 dark:bg-blue-950/40 px-3 py-2">
            <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
            <p className="text-[10px] text-blue-700 dark:text-blue-300">
              Esperando que escanees el QR en la terminal...
            </p>
          </div>
          {fallbackCmd && (
            <div className="space-y-1.5">
              <p className="text-[10px] text-blue-600 dark:text-blue-400/80">
                No se pudo abrir la terminal. Ejecuta esto manualmente:
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 rounded-lg bg-zinc-900 px-3 py-2 text-[11px] font-mono text-green-400 select-all truncate">
                  {fallbackCmd}
                </code>
                <button
                  onClick={() => handleCopy(fallbackCmd)}
                  className="shrink-0 rounded-lg border border-border bg-card p-1.5 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              </div>
            </div>
          )}
          <button
            onClick={openTerminal}
            className="text-[10px] text-blue-500 hover:text-blue-400 font-medium transition-colors"
          >
            Reintentar
          </button>
        </div>
      )}

      {error && (
        <p className="text-[10px] text-red-500 flex items-center gap-1">
          <XCircle className="h-3 w-3" />
          {error}
        </p>
      )}
    </div>
  );
}

function StatusDot({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className={`inline-block h-1.5 w-1.5 rounded-full ${ok ? "bg-emerald-500" : "bg-zinc-400"}`} />
      <span className={`text-[10px] ${ok ? "text-foreground" : "text-muted-foreground"}`}>{label}</span>
    </div>
  );
}
