"use client";

import { useState, useEffect } from "react";
import { Send, Shield, Zap, Copy, Check } from "lucide-react";
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

export interface TelegramCredentials {
  bot_username: string | null;
  bot_token_set: boolean;
  chat_id: string | null;
  webhook_url: string | null;
  webhook_secret_set: boolean;
  last_test_at: string | null;
  last_test_ok: boolean | null;
  last_test_error: string | null;
  updated_at: string | null;
}

// ─── API helpers ─────────────────────────────────────────────────────

async function updateTelegramCredentials(
  updates: { bot_username?: string | null; bot_token?: string; chat_id?: string | null }
): Promise<TelegramCredentials> {
  const res = await fetch(`${API_BASE_URL}/settings/telegram-credentials`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

async function testTelegramConnection(): Promise<ConnectionTestResult> {
  const res = await fetch(`${API_BASE_URL}/settings/test/telegram`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

// ─── Telegram Credentials ────────────────────────────────────────────

interface TelegramSectionProps {
  data: TelegramCredentials;
  onSaved: (updated: TelegramCredentials) => void;
}

export function TelegramSection({ data, onSaved }: TelegramSectionProps) {
  const [form, setForm] = useState({
    bot_username: data.bot_username ?? "",
    bot_token: "",
    chat_id: data.chat_id ?? "",
  });

  const [lastTest, setLastTest] = useState({
    at: data.last_test_at,
    ok: data.last_test_ok,
    error: data.last_test_error,
  });

  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);

  const set = (k: string) => (v: string | boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await sileo.promise(
        updateTelegramCredentials({
          bot_username: form.bot_username || null,
          chat_id: form.chat_id || null,
          ...(form.bot_token ? { bot_token: form.bot_token } : {}),
        }),
        {
          loading: { title: "Guardando credenciales Telegram..." },
          success: { title: "Credenciales Telegram guardadas" },
          error: (err: unknown) => ({
            title: "Error al guardar credenciales Telegram",
            description: err instanceof Error ? err.message : "Error desconocido.",
          }),
        }
      );
      onSaved(updated);
      setForm((prev) => ({ ...prev, bot_token: "" }));
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (): Promise<ConnectionTestResult> => {
    const r = await testTelegramConnection();
    setLastTest({ at: new Date().toISOString(), ok: r.ok, error: r.error });
    return r;
  };

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <SettingsSectionCard
        title="Credenciales Telegram"
        description="Configuracion del bot de Telegram para alertas, notificaciones y OpenClaw conversacional."
        icon={Send}
      >
        {/* Setup guide */}
        <div className="mb-5 rounded-xl border border-blue-500/20 bg-blue-50 dark:bg-blue-950/20 p-4 space-y-2">
          <p className="text-xs font-semibold text-blue-700 dark:text-blue-300">
            Como configurar tu bot de Telegram
          </p>
          <ol className="list-decimal ml-4 space-y-1 text-[11px] text-blue-600 dark:text-blue-400/80">
            <li>
              Abri <a href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer" className="font-semibold underline">@BotFather</a> en Telegram
            </li>
            <li>Manda <code className="rounded bg-blue-100 dark:bg-blue-900/40 px-1">/newbot</code> y segui las instrucciones</li>
            <li>Copia el <strong>token</strong> que te da y pegalo abajo</li>
            <li>Mandate <code className="rounded bg-blue-100 dark:bg-blue-900/40 px-1">/start</code> al bot desde tu cuenta</li>
            <li>
              Obtene tu chat_id mandando un mensaje al bot y visitando:{" "}
              <button
                onClick={() => handleCopy(`https://api.telegram.org/bot<TOKEN>/getUpdates`)}
                className="inline-flex items-center gap-1 font-mono text-blue-500 hover:text-blue-400"
              >
                /getUpdates
                {copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
              </button>
            </li>
          </ol>
        </div>

        <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
          <div>
            <FieldRow label="Username del bot" hint="Sin @, ej: ClawScoutBot">
              <TextInput
                value={form.bot_username}
                onChange={set("bot_username")}
                placeholder="ClawScoutBot"
              />
            </FieldRow>
            <FieldRow label="Chat ID" hint="Tu ID de chat personal o de grupo para recibir alertas">
              <TextInput
                value={form.chat_id}
                onChange={set("chat_id")}
                placeholder="123456789"
              />
            </FieldRow>
          </div>
          <div>
            <FieldRow
              label="Bot Token"
              hint="Dejar vacio para mantener el token actual"
            >
              <PasswordInput
                value={form.bot_token}
                onChange={set("bot_token")}
                alreadySet={data.bot_token_set}
                placeholder="4839574812:AAFDxxx..."
              />
            </FieldRow>
            <FieldRow label="Estado del token">
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
                    data.bot_token_set
                      ? "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700"
                      : "bg-amber-50 dark:bg-amber-950/30 text-amber-700"
                  }`}
                >
                  {data.bot_token_set ? "Configurado" : "No configurado"}
                </span>
                {data.bot_username && (
                  <span className="text-xs text-muted-foreground">
                    @{data.bot_username}
                  </span>
                )}
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
            <TestButton onTest={handleTest} label="Probar Telegram" />
          </div>
        </div>
      </SettingsSectionCard>

      <div className="flex items-center justify-between rounded-2xl border border-border bg-card p-4">
        <p className="text-xs text-muted-foreground">
          El bot token se guarda de forma segura. Dejar el campo vacio mantiene el token actual.
        </p>
        <SaveButton onClick={handleSave} saving={saving} />
      </div>
    </div>
  );
}

// ─── OpenClaw por Telegram ───────────────────────────────────────────

const MODEL_ROLE_OPTIONS = [
  { value: "leader", label: "Leader (rapido, 4b)", hint: "Respuestas rapidas, menor calidad" },
  { value: "executor", label: "Executor (balanceado, 9b)", hint: "Balance entre velocidad y calidad" },
  { value: "reviewer", label: "Reviewer (preciso, 27b)", hint: "Mejor calidad, mas lento y pesado" },
];

interface OpenClawTelegramProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function OpenClawTelegramSection({ data, onSaved }: OpenClawTelegramProps) {
  const [form, setForm] = useState({
    telegram_conversational_enabled: data.telegram_conversational_enabled ?? false,
    telegram_openclaw_enrichment: data.telegram_openclaw_enrichment ?? false,
    telegram_actions_enabled: data.telegram_actions_enabled ?? false,
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
      sileo.success({ title: "Configuracion de OpenClaw Telegram actualizada" });
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
      title="OpenClaw por Telegram"
      description="Conecta OpenClaw a Telegram para chatear con tu IA, consultar datos del sistema y ejecutar acciones por mensaje."
      icon={Send}
    >
      <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
        {/* Left: Feature toggles */}
        <div>
          <FieldRow
            label="Telegram conversacional"
            hint="Recibir y responder mensajes por Telegram (comandos: leads, stats, etc)"
          >
            <Toggle
              checked={form.telegram_conversational_enabled}
              onChange={toggle("telegram_conversational_enabled")}
              label={form.telegram_conversational_enabled ? "Activo" : "Inactivo"}
            />
          </FieldRow>
          <FieldRow
            label="OpenClaw IA"
            hint="Mensajes que no son comandos los responde la IA con contexto del sistema"
          >
            <Toggle
              checked={form.telegram_openclaw_enrichment}
              onChange={toggle("telegram_openclaw_enrichment")}
              label={form.telegram_openclaw_enrichment ? "Activo" : "Inactivo"}
              disabled={!form.telegram_conversational_enabled}
            />
          </FieldRow>
          <FieldRow
            label="Acciones por Telegram"
            hint="Aprobar drafts, resolver notificaciones via Telegram con confirmacion"
          >
            <Toggle
              checked={form.telegram_actions_enabled}
              onChange={toggle("telegram_actions_enabled")}
              label={form.telegram_actions_enabled ? "Activo" : "Inactivo"}
              disabled={!form.telegram_conversational_enabled}
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
                disabled={!form.telegram_openclaw_enrichment}
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
                max={4096}
                step={50}
                value={form.openclaw_max_response_chars}
                onChange={(e) => setField("openclaw_max_response_chars")(Number(e.target.value))}
                disabled={!form.telegram_openclaw_enrichment}
                className="w-full rounded-xl border border-border bg-muted px-3 py-2 text-sm text-foreground outline-none transition focus:border-border focus:bg-card disabled:opacity-50"
              />
            </FieldRow>
          </div>
        </div>

        {/* Right: Security + rate limiting */}
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <p className="font-medium text-sm text-foreground">Seguridad</p>
            </div>
            <div className="space-y-2">
              <SecurityRow label="Validacion de webhook secret" ok detail="Header X-Telegram-Bot-Api-Secret-Token" />
              <SecurityRow label="Sanitizado HTML/XSS" ok detail="Tags HTML removidos automaticamente" />
              <SecurityRow label="Truncado de input" ok detail="Maximo 500 caracteres por mensaje" />
              <SecurityRow
                label="Truncado de respuesta"
                ok
                detail={`Maximo ${form.openclaw_max_response_chars} caracteres`}
              />
              <SecurityRow
                label="Confirmacion de acciones"
                ok={form.telegram_actions_enabled}
                detail={form.telegram_actions_enabled ? "Acciones requieren confirmacion explicita" : "Acciones deshabilitadas"}
              />
            </div>
          </div>

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
              {form.openclaw_rate_limit} mensajes cada {Math.round(form.openclaw_rate_window_seconds / 60)} minutos por chat
            </p>
          </div>

          {/* Telegram-specific note about 4096 char limit */}
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-[10px] text-muted-foreground">
              <strong>Nota:</strong> Telegram tiene un limite de 4096 caracteres por mensaje.
              Las respuestas mas largas se truncan automaticamente.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <SaveButton onClick={handleSave} saving={saving} />
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
