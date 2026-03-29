"use client";

import { useState } from "react";
import { MessageCircle, Zap } from "lucide-react";
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
import { API_BASE_URL } from "@/lib/constants";

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
            <span className="rounded-xl border border-violet-700 bg-violet-600 px-4 py-2 text-sm font-medium text-white">
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

// ─── Agente Hermes 3 por WhatsApp ───────────────────────────────────

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
      const res = await fetch(`${API_BASE_URL}/settings/operational`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ whatsapp_agent_enabled: value }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const updated = await res.json();
      sileo.success({
        title: value
          ? "Agente Hermes 3 activado en WhatsApp"
          : "Agente Hermes 3 desactivado en WhatsApp",
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
      title="Agente Hermes 3"
      description="Agente IA que responde mensajes de WhatsApp automaticamente."
      icon={MessageCircle}
    >
      <FieldRow
        label="Agente Hermes 3"
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

// ─── Imports for KapsoOutreachSection ────────────────────────────────

import { Loader2, CheckCircle2, XCircle, Wifi } from "lucide-react";
