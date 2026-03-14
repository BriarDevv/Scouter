"use client";

import { useCallback, useState } from "react";
import { Mail } from "lucide-react";
import { RelativeTime } from "@/components/shared/relative-time";
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

interface MailInboundSectionProps {
  data: OperationalSettings;
  mailData: MailSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function MailInboundSection({ data, mailData, onSaved }: MailInboundSectionProps) {
  const [form, setForm] = useState({
    mail_inbound_sync_enabled: data.mail_inbound_sync_enabled ?? false,
    mail_inbound_mailbox: data.mail_inbound_mailbox ?? "",
    mail_inbound_sync_limit: String(data.mail_inbound_sync_limit ?? ""),
    mail_inbound_timeout_seconds: String(data.mail_inbound_timeout_seconds ?? ""),
    mail_inbound_search_criteria: data.mail_inbound_search_criteria ?? "",
  });

  const set = (k: string) => (v: string | boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const getData = useCallback(
    () => ({
      mail_inbound_sync_enabled: form.mail_inbound_sync_enabled,
      mail_inbound_mailbox: form.mail_inbound_mailbox || null,
      mail_inbound_sync_limit: form.mail_inbound_sync_limit
        ? parseInt(form.mail_inbound_sync_limit, 10)
        : null,
      mail_inbound_timeout_seconds: form.mail_inbound_timeout_seconds
        ? parseInt(form.mail_inbound_timeout_seconds, 10)
        : null,
      mail_inbound_search_criteria: form.mail_inbound_search_criteria || null,
    }),
    [form]
  );

  const { save, saving } = useSave(getData, onSaved);

  return (
    <SettingsSectionCard
      title="Bandeja de entrada"
      description="Configuración del canal de lectura de inbox. Credenciales IMAP en la pestaña Credenciales."
      icon={Mail}
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <StatusPill
          label={mailData.inbound.ready ? "IMAP listo" : "IMAP no listo"}
          tone={mailData.inbound.ready ? "positive" : "warning"}
        />
        {mailData.inbound.account && (
          <StatusPill label={mailData.inbound.account} tone="neutral" />
        )}
      </div>
      <FieldRow label="Habilitar sync de inbox">
        <Toggle
          checked={form.mail_inbound_sync_enabled}
          onChange={set("mail_inbound_sync_enabled") as (v: boolean) => void}
          label={form.mail_inbound_sync_enabled ? "Habilitado" : "Deshabilitado"}
        />
      </FieldRow>
      <FieldRow label="Mailbox" hint="Override del campo MAIL_IMAP_MAILBOX">
        <TextInput
          value={form.mail_inbound_mailbox}
          onChange={set("mail_inbound_mailbox")}
          placeholder={mailData.inbound.mailbox}
        />
      </FieldRow>
      <FieldRow label="Límite de sync">
        <TextInput
          value={form.mail_inbound_sync_limit}
          onChange={set("mail_inbound_sync_limit")}
          placeholder={String(mailData.inbound.sync_limit)}
          type="number"
        />
      </FieldRow>
      <FieldRow label="Timeout (seg)">
        <TextInput
          value={form.mail_inbound_timeout_seconds}
          onChange={set("mail_inbound_timeout_seconds")}
          placeholder={String(mailData.inbound.timeout_seconds)}
          type="number"
        />
      </FieldRow>
      <FieldRow label="Criterio de búsqueda IMAP">
        <TextInput
          value={form.mail_inbound_search_criteria}
          onChange={set("mail_inbound_search_criteria")}
          placeholder={mailData.inbound.search_criteria}
        />
      </FieldRow>
      {mailData.inbound.last_sync && (
        <div className="mt-4 rounded-2xl border border-border bg-muted/70 p-4">
          <p className="mb-3 text-xs font-medium text-muted-foreground">
            Última sync persistida
          </p>
          <div className="grid grid-cols-3 gap-2 text-sm">
            {(
              [
                ["Fetched", mailData.inbound.last_sync.counts.fetched],
                ["New", mailData.inbound.last_sync.counts.new],
                ["Matched", mailData.inbound.last_sync.counts.matched],
              ] as [string, number][]
            ).map(([k, v]) => (
              <div key={k} className="rounded-xl bg-card px-3 py-2">
                <p className="text-xs text-muted-foreground">{k}</p>
                <p className="font-semibold text-foreground">{v}</p>
              </div>
            ))}
          </div>
          {mailData.inbound.last_sync.at && (
            <p className="mt-2 text-xs text-muted-foreground">
              <RelativeTime date={mailData.inbound.last_sync.at} />
            </p>
          )}
        </div>
      )}
      <div className="mt-4 flex justify-end">
        <SaveButton onClick={save} saving={saving} />
      </div>
    </SettingsSectionCard>
  );
}
