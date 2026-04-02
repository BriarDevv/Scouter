"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Settings, TriangleAlert } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  getMailCredentials,
  getMailSettings,
  getOperationalSettings,
  getSetupStatus,
  getWhatsAppCredentials,
  getTelegramCredentials,
} from "@/lib/api/client";
import type {
  MailCredentials,
  MailSettings,
  OperationalSettings,
  SetupStatus,
} from "@/types";
import { TABS } from "@/components/settings/types";
import type { TabId } from "@/components/settings/types";
import { SetupChecklist } from "@/components/settings/setup-checklist";
import { BrandSection } from "@/components/settings/brand-section";
import { MailOutboundSection } from "@/components/settings/mail-outbound-section";
import { MailInboundSection } from "@/components/settings/mail-inbound-section";
import { RulesSection } from "@/components/settings/rules-section";
import { CredentialsSection } from "@/components/settings/credentials-section";
import { NotificationsSection } from "@/components/settings/notifications-section";
import { WhatsAppSection, HermesWhatsAppSection, KapsoOutreachSection } from "@/components/settings/whatsapp-section";
import { TelegramSection, HermesTelegramSection } from "@/components/settings/telegram-section";
import { TerritoriesSection } from "@/components/settings/territories-section";
import { CrawlersSection } from "@/components/settings/crawlers-section";
import type { WhatsAppCredentials } from "@/components/settings/whatsapp-section";
import type { TelegramCredentials } from "@/lib/api/client";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("setup");
  const [mailData, setMailData] = useState<MailSettings | null>(null);
  const [opData, setOpData] = useState<OperationalSettings | null>(null);
  const [credsData, setCredsData] = useState<MailCredentials | null>(null);
  const [setupData, setSetupData] = useState<SetupStatus | null>(null);
  const [waCredsData, setWaCredsData] = useState<WhatsAppCredentials | null>(null);
  const [tgCredsData, setTgCredsData] = useState<TelegramCredentials | null>(null);
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
      getMailSettings(),
      getOperationalSettings(),
      getMailCredentials(),
      getSetupStatus(),
      getWhatsAppCredentials(),
      getTelegramCredentials(),
    ]).then(([mail, op, creds, setup, waCreds, tgCreds]) => {
      if (!active) return;
      if (mail.status === "fulfilled") setMailData(mail.value);
      if (op.status === "fulfilled") setOpData(op.value);
      if (creds.status === "fulfilled") setCredsData(creds.value);
      if (setup.status === "fulfilled") setSetupData(setup.value);
      if (waCreds.status === "fulfilled") setWaCredsData(waCreds.value);
      if (tgCreds.status === "fulfilled") setTgCredsData(tgCreds.value);
      if (
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

  const handleSavedTGCreds = (updated: TelegramCredentials) => {
    setTgCredsData(updated);
    void refreshSetup();
  };

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1400px] px-8 py-8">
          <div className="space-y-6">
            <PageHeader title="Configuración" description="Ajustes operativos del sistema." />
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando configuración…
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1400px] px-8 py-8">
          <div className="space-y-6">
            <PageHeader title="Configuración" description="Ajustes operativos del sistema." />
            <EmptyState icon={Settings} title="Sin configuración disponible" description={loadError} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
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
              <KapsoOutreachSection data={opData} onSaved={handleSavedOps} />
            ) : null}
            {opData ? (
              <HermesWhatsAppSection data={opData} onSaved={handleSavedOps} />
            ) : null}
          </div>
        </TabsContent>
        <TabsContent value="telegram">
          <div className="space-y-6">
            {tgCredsData ? (
              <TelegramSection data={tgCredsData} onSaved={handleSavedTGCreds} />
            ) : <NoDataNotice />}
            {opData ? (
              <HermesTelegramSection data={opData} onSaved={handleSavedOps} />
            ) : null}
          </div>
        </TabsContent>
        <TabsContent value="territories">
          <TerritoriesSection />
        </TabsContent>
        <TabsContent value="crawlers">
          <CrawlersSection />
        </TabsContent>
      </Tabs>

      {opData?.updated_at && (
        <p className="text-xs text-muted-foreground">
          Última actualización: <RelativeTime date={opData.updated_at} />
        </p>
      )}
        </div>
      </div>
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
