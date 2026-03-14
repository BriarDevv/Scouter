"use client";

import { useState } from "react";
import { MessageCircle } from "lucide-react";
import { sileo } from "sileo";
import {
  SettingsSectionCard,
  FieldRow,
  TextInput,
  PasswordInput,
  SaveButton,
  ConnectionTestBadge,
  TestButton,
} from "./settings-primitives";
import type { ConnectionTestResult } from "@/types";
import { API_BASE_URL } from "@/lib/constants";

export interface WhatsAppCredentials {
  provider: string;
  phone_number: string | null;
  api_key_set: boolean;
  last_test_at: string | null;
  last_test_ok: boolean | null;
  last_test_error: string | null;
  updated_at: string | null;
}

interface WhatsAppSectionProps {
  data: WhatsAppCredentials;
  onSaved: (updated: WhatsAppCredentials) => void;
}

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
        description="Configuración del proveedor de mensajería WhatsApp para alertas y notificaciones."
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
            <FieldRow label="Número de teléfono" hint="Formato internacional, ej: +5491112345678">
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
              hint="Dejar vacío para mantener la clave actual"
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

      <div className="flex items-center justify-between rounded-2xl border border-border bg-card p-4">
        <p className="text-xs text-muted-foreground">
          La API key se guarda de forma segura. Dejar el campo vacío mantiene la clave actual.
        </p>
        <SaveButton onClick={handleSave} saving={saving} />
      </div>
    </div>
  );
}
