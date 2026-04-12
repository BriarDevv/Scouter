"use client";

import { useState } from "react";
import { Send, Copy, Check } from "lucide-react";
import { sileo } from "sileo";
import {
  SettingsSectionCard,
  FieldRow,
  TextInput,
  PasswordInput,
  SectionFooter,
  Toggle,
  StatusPill,
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
    <div className="space-y-4">
      <SettingsSectionCard
        title="Credenciales Telegram"
        icon={Send}
        action={
          <StatusPill
            label={data.bot_token_set ? "Configurado" : "No configurado"}
            tone={data.bot_token_set ? "positive" : "warning"}
          />
        }
      >
        {/* Setup guide */}
        <div className="mb-5 space-y-2 rounded-xl border border-border/60 bg-muted/30 p-4">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Cómo configurar tu bot
          </p>
          <ol className="ml-4 list-decimal space-y-1 text-[11px] text-muted-foreground">
            <li>
              Abrí{" "}
              <a
                href="https://t.me/BotFather"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-foreground underline decoration-border underline-offset-2 transition-colors hover:decoration-foreground/40"
              >
                @BotFather
              </a>{" "}
              en Telegram
            </li>
            <li>
              Mandá{" "}
              <code className="rounded bg-muted px-1 font-data text-foreground">/newbot</code>{" "}
              y seguí las instrucciones
            </li>
            <li>
              Copiá el <strong className="text-foreground">token</strong> y pegalo abajo
            </li>
            <li>
              Mandate{" "}
              <code className="rounded bg-muted px-1 font-data text-foreground">/start</code>{" "}
              al bot desde tu cuenta
            </li>
            <li>
              Obtené tu chat_id visitando:{" "}
              <button
                type="button"
                onClick={() =>
                  handleCopy("https://api.telegram.org/bot<TOKEN>/getUpdates")
                }
                className="inline-flex items-center gap-1 font-data text-foreground underline decoration-border underline-offset-2 transition-colors hover:decoration-foreground/40"
              >
                /getUpdates
                {copied ? (
                  <Check className="h-3 w-3 text-emerald-500" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </button>
            </li>
          </ol>
        </div>

        <FieldRow label="Username del bot">
          <TextInput
            value={form.bot_username}
            onChange={set("bot_username")}
            placeholder="ScouterBot"
          />
        </FieldRow>
        <FieldRow label="Chat ID">
          <TextInput
            value={form.chat_id}
            onChange={set("chat_id")}
            placeholder="123456789"
          />
        </FieldRow>
        <FieldRow label="Bot Token">
          <PasswordInput
            value={form.bot_token}
            onChange={set("bot_token")}
            alreadySet={data.bot_token_set}
            placeholder="4839574812:AAFDxxx..."
          />
        </FieldRow>

        <div className="mt-4 rounded-xl border border-border/60 bg-muted/30 p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Último test de conexión
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

      <SectionFooter
        updatedAt={data.updated_at}
        onSave={handleSave}
        saving={saving}
      />
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
    <SettingsSectionCard title="Agente Mote" icon={Send}>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
        <Toggle
          checked={enabled}
          onChange={handleToggle}
          label={enabled ? "Activo" : "Inactivo"}
          disabled={saving}
        />
      </div>
    </SettingsSectionCard>
  );
}
