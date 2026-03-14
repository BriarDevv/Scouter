"use client";

import { useCallback, useState } from "react";
import { Settings } from "lucide-react";
import {
  SettingsSectionCard,
  FieldRow,
  TextInput,
  Toggle,
  SaveButton,
  useSave,
} from "./settings-primitives";
import type { OperationalSettings } from "@/types";

interface RulesSectionProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function RulesSection({ data, onSaved }: RulesSectionProps) {
  const [form, setForm] = useState({
    require_approved_drafts: data.require_approved_drafts,
    auto_classify_inbound: data.auto_classify_inbound,
    reply_assistant_enabled: data.reply_assistant_enabled,
    reviewer_enabled: data.reviewer_enabled,
    reviewer_confidence_threshold: String(data.reviewer_confidence_threshold),
    prioritize_quote_replies: data.prioritize_quote_replies,
    prioritize_meeting_replies: data.prioritize_meeting_replies,
    allow_openclaw_briefs: data.allow_openclaw_briefs,
    allow_reply_assistant_generation: data.allow_reply_assistant_generation,
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
      allow_openclaw_briefs: form.allow_openclaw_briefs,
      allow_reply_assistant_generation: form.allow_reply_assistant_generation,
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
    { key: "allow_openclaw_briefs", label: "Permitir briefs de OpenClaw" },
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
      </div>
      <div className="mt-4 flex justify-end">
        <SaveButton onClick={save} saving={saving} />
      </div>
    </SettingsSectionCard>
  );
}
