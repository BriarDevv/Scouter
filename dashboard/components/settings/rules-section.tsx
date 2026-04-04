"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Settings } from "lucide-react";
import {
  SettingsSectionCard,
  FieldRow,
  TextInput,
  Toggle,
  SaveButton,
  useSave,
} from "./settings-primitives";
import { apiFetch } from "@/lib/api/client";
import type { OperationalSettings } from "@/types";

interface ResourceModeStatus {
  db_value: boolean | null;
  env_value: boolean;
  desired: boolean;
  runtime: boolean;
  restart_required: boolean;
}

interface RulesSectionProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function RulesSection({ data, onSaved }: RulesSectionProps) {
  const [resourceMode, setResourceMode] = useState<ResourceModeStatus | null>(null);

  useEffect(() => {
    apiFetch<ResourceModeStatus>("/settings/resource-mode")
      .then(setResourceMode)
      .catch(() => {});
  }, [data]);

  const [form, setForm] = useState({
    require_approved_drafts: data.require_approved_drafts,
    auto_classify_inbound: data.auto_classify_inbound,
    reply_assistant_enabled: data.reply_assistant_enabled,
    reviewer_enabled: data.reviewer_enabled,
    reviewer_confidence_threshold: String(data.reviewer_confidence_threshold),
    prioritize_quote_replies: data.prioritize_quote_replies,
    prioritize_meeting_replies: data.prioritize_meeting_replies,
    allow_reply_assistant_generation: data.allow_reply_assistant_generation,
    low_resource_mode: data.low_resource_mode ?? false,
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
      allow_reply_assistant_generation: form.allow_reply_assistant_generation,
      low_resource_mode: form.low_resource_mode,
    }),
    [form]
  );

  const { save, saving } = useSave(getData, onSaved);

  const rules: Array<{ key: keyof typeof form; label: string; hint?: string }> = [
    {
      key: "require_approved_drafts",
      label: "Requerir aprobación de drafts",
      hint: "Solo los drafts aprobados se pueden enviar",
    },
    { key: "auto_classify_inbound", label: "Clasificar replies automáticamente al sync" },
    { key: "reply_assistant_enabled", label: "Asistente de respuesta habilitado" },
    {
      key: "reviewer_enabled",
      label: "Revisor automático habilitado",
      hint: "Activa revisión profunda por el modelo reviewer",
    },
    { key: "prioritize_quote_replies", label: "Priorizar replies con pedido de cotización" },
    { key: "prioritize_meeting_replies", label: "Priorizar replies con pedido de reunión" },
    {
      key: "allow_reply_assistant_generation",
      label: "Permitir generación de respuestas asistidas",
    },
  ];

  return (
    <SettingsSectionCard
      title="Reglas de automatización"
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
          hint="Valor entre 0 y 1 — mensajes por debajo del umbral se marcan para revisión manual"
        >
          <TextInput
            value={form.reviewer_confidence_threshold}
            onChange={set("reviewer_confidence_threshold")}
            placeholder="0.7"
            type="number"
          />
        </FieldRow>
        <FieldRow
          label="Modo bajo recurso (LOW_RESOURCE_MODE)"
          hint="Un solo worker, una cola, modelos secuenciales. Para notebooks sin GPU dedicada."
        >
          <Toggle
            checked={form.low_resource_mode}
            onChange={set("low_resource_mode") as (v: boolean) => void}
            label={form.low_resource_mode ? "Activado" : "Desactivado"}
          />
        </FieldRow>
      </div>

      {resourceMode?.restart_required && (
        <div className="mt-3 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-medium">Reinicio de workers requerido</p>
            <p className="mt-0.5 text-xs opacity-80">
              El modo de recursos cambió pero los workers siguen corriendo con la config anterior.
              Ejecutá <code className="rounded bg-amber-100 px-1 dark:bg-amber-900/30">make restart-workers</code> para aplicar.
            </p>
          </div>
        </div>
      )}

      <div className="mt-4 flex justify-end">
        <SaveButton onClick={save} saving={saving} />
      </div>
    </SettingsSectionCard>
  );
}
