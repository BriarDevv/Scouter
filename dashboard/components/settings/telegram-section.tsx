"use client";

import { useState } from "react";
import { Send, Copy, Check } from "lucide-react";
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
import type { OperationalSettings } from "@/types";
import {
  updateTelegramCredentials,
  testTelegramConnection,
  updateOperationalSettings,
} from "@/lib/api/client";
import type { TelegramCredentials } from "@/lib/api/client";

export type { TelegramCredentials };

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
        description="Configuracion del bot de Telegram para alertas y notificaciones."
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

// ─── Agente Mote por Telegram ───────────────────────────────────

interface HermesTelegramProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function HermesTelegramSection({ data, onSaved }: HermesTelegramProps) {
  const [enabled, setEnabled] = useState(data.telegram_agent_enabled ?? false);
  const [saving, setSaving] = useState(false);

  const handleToggle = async (value: boolean) => {
    setEnabled(value);
    setSaving(true);
    try {
      const updated = await updateOperationalSettings({ telegram_agent_enabled: value });
      sileo.success({
        title: value
          ? "Agente Mote activado en Telegram"
          : "Agente Mote desactivado en Telegram",
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

  return (
    <SettingsSectionCard
      title="Agente Mote"
      description="Agente IA que responde mensajes de Telegram automaticamente."
      icon={Send}
    >
      <FieldRow
        label="Agente Mote"
        hint="Responde mensajes con IA"
      >
        <Toggle
          checked={enabled}
          onChange={handleToggle}
          label={enabled ? "Activo" : "Inactivo"}
          disabled={saving}
        />
      </FieldRow>
    </SettingsSectionCard>
  );
}
