"use client";

import { useRef, useState } from "react";
import { KeyRound } from "lucide-react";
import { sileo } from "sileo";
import {
  SettingsSectionCard,
  FieldRow,
  TextInput,
  PasswordInput,
  Toggle,
  SectionFooter,
  ProviderPicker,
  ConnectionTestBadge,
  TestButton,
} from "./settings-primitives";
import { SMTP_PRESETS, IMAP_PRESETS } from "./mail-presets";
import type { MailProvider } from "./mail-presets";
import {
  updateMailCredentials,
  testSmtpConnection,
  testImapConnection,
} from "@/lib/api/client";
import type { ConnectionTestResult, MailCredentials } from "@/types";

interface CredentialsSectionProps {
  data: MailCredentials;
  onSaved: (updated: MailCredentials) => void;
}

export function CredentialsSection({ data, onSaved }: CredentialsSectionProps) {
  const [smtpProvider, setSmtpProvider] = useState<MailProvider>("custom");
  const [imapProvider, setImapProvider] = useState<MailProvider>("custom");

  const [smtpForm, setSmtpForm] = useState({
    smtp_host: data.smtp_host ?? "",
    smtp_port: String(data.smtp_port),
    smtp_username: data.smtp_username ?? "",
    smtp_password: "",
    smtp_ssl: data.smtp_ssl,
    smtp_starttls: data.smtp_starttls,
  });

  const [imapForm, setImapForm] = useState({
    imap_host: data.imap_host ?? "",
    imap_port: String(data.imap_port),
    imap_username: data.imap_username ?? "",
    imap_password: "",
    imap_ssl: data.imap_ssl,
  });

  const [smtpLastTest, setSmtpLastTest] = useState({
    at: data.smtp_last_test_at,
    ok: data.smtp_last_test_ok,
    error: data.smtp_last_test_error,
  });

  const [imapLastTest, setImapLastTest] = useState({
    at: data.imap_last_test_at,
    ok: data.imap_last_test_ok,
    error: data.imap_last_test_error,
  });

  const [saving, setSaving] = useState(false);

  const setSmtp = (k: string) => (v: string | boolean) =>
    setSmtpForm((prev) => ({ ...prev, [k]: v }));
  const setImap = (k: string) => (v: string | boolean) =>
    setImapForm((prev) => ({ ...prev, [k]: v }));

  const applySmtpPreset = (p: MailProvider) => {
    setSmtpProvider(p);
    const preset = SMTP_PRESETS[p];
    if (preset) {
      setSmtpForm((prev) => ({
        ...prev,
        smtp_host: preset.host,
        smtp_port: String(preset.port),
        smtp_ssl: preset.ssl,
        smtp_starttls: preset.starttls,
      }));
    }
  };

  const applyImapPreset = (p: MailProvider) => {
    setImapProvider(p);
    const preset = IMAP_PRESETS[p];
    if (preset) {
      setImapForm((prev) => ({
        ...prev,
        imap_host: preset.host,
        imap_port: String(preset.port),
        imap_ssl: preset.ssl,
      }));
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await sileo.promise(
        updateMailCredentials({
          smtp_host: smtpForm.smtp_host || null,
          smtp_port: parseInt(smtpForm.smtp_port, 10) || 587,
          smtp_username: smtpForm.smtp_username || null,
          smtp_ssl: smtpForm.smtp_ssl,
          smtp_starttls: smtpForm.smtp_starttls,
          imap_host: imapForm.imap_host || null,
          imap_port: parseInt(imapForm.imap_port, 10) || 993,
          imap_username: imapForm.imap_username || null,
          imap_ssl: imapForm.imap_ssl,
          ...(smtpForm.smtp_password ? { smtp_password: smtpForm.smtp_password } : {}),
          ...(imapForm.imap_password ? { imap_password: imapForm.imap_password } : {}),
        }),
        {
          loading: { title: "Guardando credenciales…" },
          success: { title: "Credenciales guardadas" },
          error: (err: unknown) => ({
            title: "Error al guardar credenciales",
            description: err instanceof Error ? err.message : "Error desconocido.",
          }),
        }
      );
      onSaved(updated);
      setSmtpForm((prev) => ({ ...prev, smtp_password: "" }));
      setImapForm((prev) => ({ ...prev, imap_password: "" }));
    } finally {
      setSaving(false);
    }
  };

  const handleSmtpTest = async (): Promise<ConnectionTestResult> => {
    const r = await testSmtpConnection();
    setSmtpLastTest({ at: new Date().toISOString(), ok: r.ok, error: r.error });
    return r;
  };

  const handleImapTest = async (): Promise<ConnectionTestResult> => {
    const r = await testImapConnection();
    setImapLastTest({ at: new Date().toISOString(), ok: r.ok, error: r.error });
    return r;
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2 lg:items-stretch [&>section]:h-full">
      <SettingsSectionCard
        title="Credenciales SMTP"
        description="Servidor de salida de correo. Las contraseñas se guardan en DB y nunca se exponen por API."
        icon={KeyRound}
      >
        <div className="mb-5">
          <p className="mb-2 text-xs font-medium text-muted-foreground">Proveedor</p>
          <ProviderPicker value={smtpProvider} onChange={applySmtpPreset} />
        </div>
        <FieldRow label="Servidor SMTP">
          <TextInput
            value={smtpForm.smtp_host}
            onChange={setSmtp("smtp_host")}
            placeholder="smtp.gmail.com"
          />
        </FieldRow>
        <FieldRow label="Puerto">
          <TextInput
            value={smtpForm.smtp_port}
            onChange={setSmtp("smtp_port")}
            placeholder="587"
            type="number"
          />
        </FieldRow>
        <FieldRow label="Usuario / Email">
          <TextInput
            value={smtpForm.smtp_username}
            onChange={setSmtp("smtp_username")}
            placeholder="vos@gmail.com"
            type="email"
          />
        </FieldRow>
        <FieldRow
          label="Contraseña"
          hint="Dejar vacío para mantener la contraseña actual"
        >
          <PasswordInput
            value={smtpForm.smtp_password}
            onChange={setSmtp("smtp_password")}
            alreadySet={data.smtp_password_set}
          />
        </FieldRow>
        <div className="grid grid-cols-2 gap-x-4 py-2.5">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-foreground/80">SSL/TLS</label>
            <Toggle
              checked={smtpForm.smtp_ssl}
              onChange={setSmtp("smtp_ssl") as (v: boolean) => void}
              label={smtpForm.smtp_ssl ? "SSL activo" : "Sin SSL"}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-foreground/80">STARTTLS</label>
            <Toggle
              checked={smtpForm.smtp_starttls}
              onChange={setSmtp("smtp_starttls") as (v: boolean) => void}
              label={smtpForm.smtp_starttls ? "STARTTLS activo" : "Sin STARTTLS"}
            />
          </div>
        </div>
        <div className="mt-4 rounded-xl border border-border/60 bg-muted/30 p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Último test de conexión
              </p>
              <ConnectionTestBadge
                lastAt={smtpLastTest.at}
                lastOk={smtpLastTest.ok}
                lastError={smtpLastTest.error}
              />
            </div>
            <TestButton onTest={handleSmtpTest} label="Probar SMTP" />
          </div>
        </div>
      </SettingsSectionCard>

      <SettingsSectionCard
        title="Credenciales IMAP"
        description="Servidor de entrada de correo para sincronización de inbox."
        icon={KeyRound}
      >
        <div className="mb-5">
          <p className="mb-2 text-xs font-medium text-muted-foreground">Proveedor</p>
          <ProviderPicker value={imapProvider} onChange={applyImapPreset} />
        </div>
        <FieldRow label="Servidor IMAP">
          <TextInput
            value={imapForm.imap_host}
            onChange={setImap("imap_host")}
            placeholder="imap.gmail.com"
          />
        </FieldRow>
        <FieldRow label="Puerto">
          <TextInput
            value={imapForm.imap_port}
            onChange={setImap("imap_port")}
            placeholder="993"
            type="number"
          />
        </FieldRow>
        <FieldRow label="Usuario / Email">
          <TextInput
            value={imapForm.imap_username}
            onChange={setImap("imap_username")}
            placeholder="vos@gmail.com"
            type="email"
          />
        </FieldRow>
        <FieldRow
          label="Contraseña"
          hint="Dejar vacío para mantener la contraseña actual"
        >
          <PasswordInput
            value={imapForm.imap_password}
            onChange={setImap("imap_password")}
            alreadySet={data.imap_password_set}
          />
        </FieldRow>
        <FieldRow label="SSL/TLS">
          <Toggle
            checked={imapForm.imap_ssl}
            onChange={setImap("imap_ssl") as (v: boolean) => void}
            label={imapForm.imap_ssl ? "SSL activo" : "Sin SSL"}
          />
        </FieldRow>
        <div className="mt-4 rounded-xl border border-border/60 bg-muted/30 p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Último test de conexión
              </p>
              <ConnectionTestBadge
                lastAt={imapLastTest.at}
                lastOk={imapLastTest.ok}
                lastError={imapLastTest.error}
              />
            </div>
            <TestButton onTest={handleImapTest} label="Probar IMAP" />
          </div>
        </div>
      </SettingsSectionCard>
      </div>

      <SectionFooter
        updatedAt={data.updated_at}
        onSave={handleSave}
        saving={saving}
      />
    </div>
  );
}
