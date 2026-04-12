"use client";

import { useCallback, useState } from "react";
import { Inbox, Mail } from "lucide-react";
import { RelativeTime } from "@/components/shared/relative-time";
import {
  FieldRow,
  SectionFooter,
  SettingsSectionCard,
  StatusPill,
  TextInput,
  Toggle,
  useSave,
} from "./settings-primitives";
import type { MailSettings, OperationalSettings } from "@/types";

interface MailIOSectionProps {
  data: OperationalSettings;
  mailData: MailSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function MailIOSection({ data, mailData, onSaved }: MailIOSectionProps) {
  const [form, setForm] = useState({
    // Salida
    mail_enabled: data.mail_enabled ?? false,
    mail_from_email: data.mail_from_email ?? "",
    mail_from_name: data.mail_from_name ?? "",
    mail_reply_to: data.mail_reply_to ?? "",
    mail_send_timeout_seconds: String(data.mail_send_timeout_seconds ?? ""),
    require_approved_drafts: data.require_approved_drafts,
    // Entrada
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
      mail_enabled: form.mail_enabled,
      mail_from_email: form.mail_from_email || null,
      mail_from_name: form.mail_from_name || null,
      mail_reply_to: form.mail_reply_to || null,
      mail_send_timeout_seconds: form.mail_send_timeout_seconds
        ? parseInt(form.mail_send_timeout_seconds, 10)
        : null,
      require_approved_drafts: form.require_approved_drafts,
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
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2 lg:items-start">
        {/* ── Mail de salida ─────────────────────────── */}
        <SettingsSectionCard
          title="Mail de salida"
          description="Canal de envío. Las credenciales SMTP están en Credenciales."
          icon={Mail}
        >
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
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

            {/* Toggles arriba */}
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
              <Toggle
                checked={form.mail_enabled}
                onChange={set("mail_enabled") as (v: boolean) => void}
                label={
                  form.mail_enabled ? "Envío habilitado" : "Envío deshabilitado"
                }
              />
              <Toggle
                checked={form.require_approved_drafts}
                onChange={set("require_approved_drafts") as (v: boolean) => void}
                label={
                  form.require_approved_drafts
                    ? "Solo drafts aprobados"
                    : "Sin restricción de drafts"
                }
              />
            </div>

            <FieldRow label="From Email" hint="Override del MAIL_FROM_EMAIL">
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
          </div>
        </SettingsSectionCard>

        {/* ── Bandeja de entrada ─────────────────────── */}
        <SettingsSectionCard
          title="Bandeja de entrada"
          description="Canal de lectura. Las credenciales IMAP están en Credenciales."
          icon={Inbox}
        >
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <StatusPill
                label={mailData.inbound.ready ? "IMAP listo" : "IMAP no listo"}
                tone={mailData.inbound.ready ? "positive" : "warning"}
              />
              {mailData.inbound.account && (
                <StatusPill label={mailData.inbound.account} tone="neutral" />
              )}
            </div>

            <div className="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
              <Toggle
                checked={form.mail_inbound_sync_enabled}
                onChange={
                  set("mail_inbound_sync_enabled") as (v: boolean) => void
                }
                label={
                  form.mail_inbound_sync_enabled
                    ? "Sync habilitado"
                    : "Sync deshabilitado"
                }
              />
            </div>

            <FieldRow label="Mailbox" hint="Override del MAIL_IMAP_MAILBOX">
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
            <FieldRow label="Criterio IMAP">
              <TextInput
                value={form.mail_inbound_search_criteria}
                onChange={set("mail_inbound_search_criteria")}
                placeholder={mailData.inbound.search_criteria}
              />
            </FieldRow>

            {mailData.inbound.last_sync && (
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Última sync persistida
                </p>
                <div className="grid grid-cols-3 gap-2">
                  {(
                    [
                      ["Fetched", mailData.inbound.last_sync.counts.fetched],
                      ["New", mailData.inbound.last_sync.counts.new],
                      ["Matched", mailData.inbound.last_sync.counts.matched],
                    ] as [string, number][]
                  ).map(([k, v]) => (
                    <div
                      key={k}
                      className="rounded-lg border border-border/60 bg-card px-3 py-2"
                    >
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                        {k}
                      </p>
                      <p className="font-data text-sm font-semibold text-foreground">
                        {v}
                      </p>
                    </div>
                  ))}
                </div>
                {mailData.inbound.last_sync.at && (
                  <p className="mt-2 text-[11px] text-muted-foreground">
                    <RelativeTime date={mailData.inbound.last_sync.at} />
                  </p>
                )}
              </div>
            )}
          </div>
        </SettingsSectionCard>
      </div>

      <SectionFooter
        updatedAt={data.updated_at}
        onSave={save}
        saving={saving}
      />
    </div>
  );
}
