"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Settings, TriangleAlert } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  getMailCredentials,
  getLLMSettings,
  getMailSettings,
  getOperationalSettings,
  getSetupStatus,
} from "@/lib/api/client";
import { API_BASE_URL } from "@/lib/constants";
import type {
  LLMSettings,
  MailCredentials,
  MailSettings,
  OperationalSettings,
  SetupStatus,
} from "@/types";
import { TABS } from "@/components/settings/types";
import type { TabId } from "@/components/settings/types";
import { SetupChecklist } from "@/components/settings/setup-checklist";
import { LLMSection } from "@/components/settings/llm-section";
import { BrandSection } from "@/components/settings/brand-section";
import { MailOutboundSection } from "@/components/settings/mail-outbound-section";
import { MailInboundSection } from "@/components/settings/mail-inbound-section";
import { RulesSection } from "@/components/settings/rules-section";
import { CredentialsSection } from "@/components/settings/credentials-section";
import { NotificationsSection } from "@/components/settings/notifications-section";
import { WhatsAppSection, OpenClawWhatsAppSection } from "@/components/settings/whatsapp-section";
import { AIWorkspaceSection } from "@/components/settings/ai-workspace-section";
import { TerritoriesSection } from "@/components/settings/territories-section";
import type { WhatsAppCredentials } from "@/components/settings/whatsapp-section";

async function getWhatsAppCredentials(): Promise<WhatsAppCredentials> {
  const res = await fetch(`${API_BASE_URL}/settings/whatsapp-credentials`);
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("setup");
  const [llmData, setLlmData] = useState<LLMSettings | null>(null);
  const [mailData, setMailData] = useState<MailSettings | null>(null);
  const [opData, setOpData] = useState<OperationalSettings | null>(null);
  const [credsData, setCredsData] = useState<MailCredentials | null>(null);
  const [setupData, setSetupData] = useState<SetupStatus | null>(null);
  const [waCredsData, setWaCredsData] = useState<WhatsAppCredentials | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refreshSetup = useCallback(async () => {
    try {
      setSetupData(await getSetupStatus());
    } catch { /* non-critical */ }
  }, []);

  const refreshMail = useCallback(async () => {
    try {
      setMailData(await getMailSettings());
    } catch { /* non-critical */ }
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(null);

    Promise.allSettled([
      getLLMSettings(),
      getMailSettings(),
      getOperationalSettings(),
      getMailCredentials(),
      getSetupStatus(),
      getWhatsAppCredentials(),
    ]).then(([llm, mail, op, creds, setup, waCreds]) => {
      if (!active) return;
      if (llm.status === "fulfilled") setLlmData(llm.value);
      if (mail.status === "fulfilled") setMailData(mail.value);
      if (op.status === "fulfilled") setOpData(op.value);
      if (creds.status === "fulfilled") setCredsData(creds.value);
      if (setup.status === "fulfilled") setSetupData(setup.value);
      if (waCreds.status === "fulfilled") setWaCredsData(waCreds.value);
      if (
        llm.status === "rejected" &&
        mail.status === "rejected" &&
        op.status === "rejected"
      ) {
        setLoadError("No se pudo conectar con el backend.");
      }
      setLoading(false);
    });

    return () => { active = false; };
  }, []);

  const handleSavedOps = (updated: OperationalSettings) => {
    setOpData(updated);
    void refreshSetup();
    void refreshMail();
  };

  const handleSavedCreds = (updated: MailCredentials) => {
    setCredsData(updated);
    void refreshSetup();
    void refreshMail();
  };

  const handleSavedWACreds = (updated: WhatsAppCredentials) => {
    setWaCredsData(updated);
    void refreshSetup();
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Configuración" description="Ajustes operativos del sistema." />
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando configuración…
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="space-y-6">
        <PageHeader title="Configuración" description="Ajustes operativos del sistema." />
        <EmptyState icon={Settings} title="Sin configuración disponible" description={loadError} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Configuración" description="Ajustes operativos del sistema." />

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabId)}>
        <TabsList className="h-auto flex-wrap gap-1 rounded-2xl p-1">
          {TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id} className="rounded-xl px-4 py-2">
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="setup">
          {setupData ? (
            <SetupChecklist data={setupData} onTabChange={setActiveTab} />
          ) : <NoDataNotice />}
        </TabsContent>
        <TabsContent value="brand">
          {opData ? (
            <BrandSection data={opData} onSaved={handleSavedOps} />
          ) : <NoDataNotice />}
        </TabsContent>
        <TabsContent value="mail_out">
          {opData && mailData ? (
            <MailOutboundSection data={opData} mailData={mailData} onSaved={handleSavedOps} />
          ) : <NoDataNotice />}
        </TabsContent>
        <TabsContent value="mail_in">
          {opData && mailData ? (
            <MailInboundSection data={opData} mailData={mailData} onSaved={handleSavedOps} />
          ) : <NoDataNotice />}
        </TabsContent>
        <TabsContent value="rules">
          {opData ? (
            <RulesSection data={opData} onSaved={handleSavedOps} />
          ) : <NoDataNotice />}
        </TabsContent>
        <TabsContent value="credentials">
          {credsData ? (
            <CredentialsSection data={credsData} onSaved={handleSavedCreds} />
          ) : <NoDataNotice />}
        </TabsContent>
        <TabsContent value="llm">
          {llmData ? <LLMSection data={llmData} /> : <NoDataNotice />}
        </TabsContent>
        <TabsContent value="notifications">
          {opData ? (
            <NotificationsSection data={opData} onSaved={handleSavedOps} />
          ) : <NoDataNotice />}
        </TabsContent>
        <TabsContent value="whatsapp">
          <div className="space-y-6">
            {waCredsData ? (
              <WhatsAppSection data={waCredsData} onSaved={handleSavedWACreds} />
            ) : <NoDataNotice />}
            {opData ? (
              <OpenClawWhatsAppSection data={opData} onSaved={handleSavedOps} />
            ) : null}
          </div>
        </TabsContent>
        <TabsContent value="ai-workspace">
          <AIWorkspaceSection />
        </TabsContent>
        <TabsContent value="territories">
          <TerritoriesSection />
        </TabsContent>
      </Tabs>

      {opData?.updated_at && (
        <p className="text-xs text-muted-foreground">
          Última actualización: <RelativeTime date={opData.updated_at} />
        </p>
      )}
    </div>
  );
}

function NoDataNotice() {
  return (
    <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
      <div className="flex items-center gap-2">
        <TriangleAlert className="h-4 w-4 text-amber-500" />
        No se pudieron cargar los datos para esta sección.
      </div>
    </div>
  );
}
