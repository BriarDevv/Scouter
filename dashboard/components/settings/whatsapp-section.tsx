"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, MessageCircle, Wifi, XCircle, Zap } from "lucide-react";
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
  updateWhatsAppCredentials,
  testWhatsApp,
  updateOperationalSettings,
  testKapsoConnection,
  getKapsoApiKeyStatus,
  updateKapsoApiKey,
} from "@/lib/api/client";

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
    const r = await testWhatsApp();
    const result: ConnectionTestResult = { ok: r.ok, error: r.error ?? null, sample_count: null };
    setLastTest({ at: new Date().toISOString(), ok: result.ok, error: result.error });
    return result;
  };

  return (
    <div className="space-y-4">
      <SettingsSectionCard
        title="Credenciales WhatsApp"
        icon={MessageCircle}
        action={
          <StatusPill
            label={data.api_key_set ? "Configurada" : "No configurada"}
            tone={data.api_key_set ? "positive" : "warning"}
          />
        }
      >
        <FieldRow label="Número de teléfono">
          <TextInput
            value={form.phone_number}
            onChange={set("phone_number")}
            placeholder="+5491112345678"
          />
        </FieldRow>
        <FieldRow label="API Key">
          <PasswordInput
            value={form.api_key}
            onChange={set("api_key")}
            alreadySet={data.api_key_set}
            placeholder="API key de CallMeBot"
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
            <TestButton onTest={handleTest} label="Probar WhatsApp" />
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

// ─── Agente Mote por WhatsApp ───────────────────────────────────

interface HermesWhatsAppProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function HermesWhatsAppSection({ data, onSaved }: HermesWhatsAppProps) {
  const [enabled, setEnabled] = useState(data.whatsapp_agent_enabled ?? false);
  const [saving, setSaving] = useState(false);

  const handleToggle = async (value: boolean) => {
    setEnabled(value);
    setSaving(true);
    try {
      const updated = await updateOperationalSettings({ whatsapp_agent_enabled: value });
      sileo.success({
        title: value
          ? "Agente Mote activado en WhatsApp"
          : "Agente Mote desactivado en WhatsApp",
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
    <SettingsSectionCard title="Agente Mote" icon={MessageCircle}>
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

// ─── Kapso WhatsApp Outreach ────────────────────────────────────────

interface KapsoOutreachSectionProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function KapsoOutreachSection({ data, onSaved }: KapsoOutreachSectionProps) {
  const [enabled, setEnabled] = useState(data.whatsapp_outreach_enabled ?? false);
  const [apiKey, setApiKey] = useState("");
  const [apiKeySet, setApiKeySet] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savingKey, setSavingKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null);

  useEffect(() => {
    getKapsoApiKeyStatus()
      .then((status) => setApiKeySet(status.configured))
      .catch(() => {});
  }, []);

  const handleToggle = async (value: boolean) => {
    setEnabled(value);
    setSaving(true);
    try {
      const updated = await updateOperationalSettings({ whatsapp_outreach_enabled: value });
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

  const handleSaveKey = async () => {
    if (!apiKey.trim()) return;
    setSavingKey(true);
    try {
      const result = await sileo.promise(
        updateKapsoApiKey(apiKey),
        {
          loading: { title: "Guardando API key de Kapso..." },
          success: { title: "API key de Kapso guardada" },
          error: (err: unknown) => ({
            title: "Error al guardar API key",
            description: err instanceof Error ? err.message : "Error desconocido.",
          }),
        }
      );
      setApiKeySet(result.configured);
      setApiKey("");
    } finally {
      setSavingKey(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testKapsoConnection();
      setTestResult(result);
      if (result.status === "ok") {
        sileo.success({ title: "Kapso: conexión exitosa" });
      } else {
        sileo.error({ title: "Kapso: falló la conexión", description: result.message });
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
    <div className="space-y-4">
      <SettingsSectionCard
        title="Outreach por WhatsApp (Kapso)"
        icon={MessageCircle}
        action={
          <StatusPill
            label={apiKeySet ? "API key configurada" : "Sin API key"}
            tone={apiKeySet ? "positive" : "warning"}
          />
        }
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
            <Toggle
              checked={enabled}
              onChange={handleToggle}
              label={enabled ? "Outreach activo" : "Outreach inactivo"}
              disabled={saving}
            />
          </div>

          <FieldRow label="API Key de Kapso">
            <PasswordInput
              value={apiKey}
              onChange={setApiKey}
              alreadySet={apiKeySet}
              placeholder="API key de Kapso"
            />
          </FieldRow>

          <div className="rounded-xl border border-border/60 bg-muted/30 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="mb-1.5 flex items-center gap-2">
                  <Zap className="h-3.5 w-3.5 text-foreground" />
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Conexión Kapso
                  </p>
                </div>
                {testResult ? (
                  <div className="flex items-center gap-1.5">
                    {testResult.status === "ok" ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-rose-500" />
                    )}
                    <span
                      className={`text-xs font-medium ${
                        testResult.status === "ok"
                          ? "text-emerald-700 dark:text-emerald-300"
                          : "text-rose-700 dark:text-rose-300"
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
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted active:translate-y-px disabled:opacity-50"
              >
                {testing ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Wifi className="h-3.5 w-3.5" />
                )}
                Testear conexión
              </button>
            </div>
          </div>
        </div>
      </SettingsSectionCard>

      <SectionFooter
        updatedAt={data.updated_at}
        onSave={handleSaveKey}
        saving={savingKey}
      />
    </div>
  );
}
