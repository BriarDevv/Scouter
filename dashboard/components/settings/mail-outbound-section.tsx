"use client";

import { useCallback, useState } from "react";
import { Mail } from "lucide-react";
import {
  SettingsSectionCard,
  StatusPill,
  FieldRow,
  TextInput,
  Toggle,
  SaveButton,
  useSave,
} from "./settings-primitives";
import type { MailSettings, OperationalSettings } from "@/types";

interface MailOutboundSectionProps {
  data: OperationalSettings;
  mailData: MailSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function MailOutboundSection({ data, mailData, onSaved }: MailOutboundSectionProps) {
  const [form, setForm] = useState({
    mail_enabled: data.mail_enabled ?? false,
    mail_from_email: data.mail_from_email ?? "",
    mail_from_name: data.mail_from_name ?? "",
    mail_reply_to: data.mail_reply_to ?? "",
    mail_send_timeout_seconds: String(data.mail_send_timeout_seconds ?? ""),
    require_approved_drafts: data.require_approved_drafts,
  });

  const set = (k: string) => (v: string | boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const getData = useCallback(
    () => ({
      mail_enabled: form.mail_enabled,
      mail_from_email: form.mail_from_email || null,
      mail_from_name: form.mail_from_name || null,
      mail_reply_to: form.mail_reply_to || null,
      mail_send_timeout_seconds: form.mail_send_timeout_seconds
        ? parseInt(form.mail_send_timeout_seconds, 10)
        : null,
      require_approved_drafts: form.require_approved_drafts,
    }),
    [form]
  );

  const { save, saving } = useSave(getData, onSaved);

  return (
    <SettingsSectionCard
      title="Mail de salida"
      description="Configuración operativa del canal de envío. Credenciales SMTP en la pestaña Credenciales."
      icon={Mail}
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <StatusPill
          label={mailData.outbound.ready ? "SMTP listo" : "SMTP no listo"}
          tone={mailData.outbound.ready ? "positive" : "warning"}
        />
        {mailData.outbound.missing_requirements.length > 0 && (
          <StatusPill
            label={`Falta: ${mailData.outbound.missing_requirements.join(", ")}`}
            tone="danger"
          />
        )}
      </div>
      <FieldRow label="Habilitar envío de mail">
        <Toggle
          checked={form.mail_enabled}
          onChange={set("mail_enabled") as (v: boolean) => void}
          label={form.mail_enabled ? "Habilitado" : "Deshabilitado"}
        />
      </FieldRow>
      <FieldRow label="From Email" hint="Override del campo MAIL_FROM_EMAIL">
        <TextInput
          value={form.mail_from_email}
          onChange={set("mail_from_email")}
          placeholder={mailData.outbound.from_email ?? "Usa valor de .env"}
          type="email"
        />
      </FieldRow>
      <FieldRow label="From Name">
        <TextInput
          value={form.mail_from_name}
          onChange={set("mail_from_name")}
          placeholder={mailData.outbound.from_name}
        />
      </FieldRow>
      <FieldRow label="Reply-To">
        <TextInput
          value={form.mail_reply_to}
          onChange={set("mail_reply_to")}
          placeholder={mailData.outbound.reply_to ?? "Sin reply-to"}
          type="email"
        />
      </FieldRow>
      <FieldRow label="Timeout de envío (seg)">
        <TextInput
          value={form.mail_send_timeout_seconds}
          onChange={set("mail_send_timeout_seconds")}
          placeholder={String(mailData.outbound.send_timeout_seconds)}
          type="number"
        />
      </FieldRow>
      <FieldRow label="Requerir aprobación de drafts">
        <Toggle
          checked={form.require_approved_drafts}
          onChange={set("require_approved_drafts") as (v: boolean) => void}
          label={form.require_approved_drafts ? "Solo drafts aprobados" : "Sin restricción"}
        />
      </FieldRow>
      <div className="mt-4 flex justify-end">
        <SaveButton onClick={save} saving={saving} />
      </div>
    </SettingsSectionCard>
  );
}
