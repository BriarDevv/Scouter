"use client";

import Link from "next/link";
import { useState } from "react";
import { Loader2, Settings, TriangleAlert } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import type {
  MailCredentials,
  MailSettings,
  OperationalSettings,
  SetupReadiness,
  SetupStatus,
} from "@/types";
import { TABS } from "@/components/settings/types";
import type {
  DataSubTab,
  EmailSubTab,
  TabId,
  TelegramSubTab,
  WhatsAppSubTab,
} from "@/components/settings/types";
import { SetupChecklist } from "@/components/settings/setup-checklist";
import { BrandSection } from "@/components/settings/brand-section";
import { EmailSection } from "@/components/settings/email-section";
import { AutomationRulesSection } from "@/components/settings/automation-rules-section";
import { NotificationsSection } from "@/components/settings/notifications-section";
import { WhatsAppTabSection } from "@/components/settings/whatsapp-tab-section";
import { TelegramTabSection } from "@/components/settings/telegram-tab-section";
import { DataSection } from "@/components/settings/data-section";
import type { WhatsAppCredentials } from "@/components/settings/whatsapp-section";
import type { TelegramCredentials } from "@/lib/api/client";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("setup");
  const [emailSubTab, setEmailSubTab] = useState<EmailSubTab>("mail");
  const [dataSubTab, setDataSubTab] = useState<DataSubTab>("territories");
  const [waSubTab, setWaSubTab] = useState<WhatsAppSubTab>("alerts");
  const [tgSubTab, setTgSubTab] = useState<TelegramSubTab>("bot");

  const { data: mailData, isLoading: mailLoading, mutate: mutateMail } =
    useApi<MailSettings>("/settings/mail");
  const { data: opData, isLoading: opLoading, mutate: mutateOp } =
    useApi<OperationalSettings>("/settings/operational");
  const { data: credsData, mutate: mutateCreds } =
    useApi<MailCredentials>("/settings/mail-credentials");
  const { data: setupData, mutate: mutateSetup } =
    useApi<SetupStatus>("/settings/setup-status");
  const { data: readiness, mutate: mutateReadiness } =
    useApi<SetupReadiness>("/setup/readiness");
  const { data: waCredsData, mutate: mutateWaCreds } =
    useApi<WhatsAppCredentials>("/settings/whatsapp-credentials");
  const { data: tgCredsData, mutate: mutateTgCreds } =
    useApi<TelegramCredentials>("/settings/telegram-credentials");

  const loading = mailLoading || opLoading;
  const loadError =
    !loading && !mailData && !opData ? "No se pudo conectar con el backend." : null;

  const refreshSetup = async () => {
    await Promise.all([mutateSetup(), mutateReadiness()]);
  };

  const refreshMail = async () => {
    await mutateMail();
  };

  const handleSavedOps = (updated: OperationalSettings) => {
    void mutateOp(updated, false);
    void refreshSetup();
    void refreshMail();
  };

  const handleSavedCreds = (updated: MailCredentials) => {
    void mutateCreds(updated, false);
    void refreshSetup();
    void refreshMail();
  };

  const handleSavedWACreds = (updated: WhatsAppCredentials) => {
    void mutateWaCreds(updated, false);
    void refreshSetup();
  };

  const handleSavedTGCreds = (updated: TelegramCredentials) => {
    void mutateTgCreds(updated, false);
    void refreshSetup();
  };

  // Setup checklist deep-links into tab + sub-tab
  const handleTabChange = (tab: TabId, subTab?: string) => {
    setActiveTab(tab);
    if (tab === "email" && subTab) setEmailSubTab(subTab as EmailSubTab);
    else if (tab === "data" && subTab) setDataSubTab(subTab as DataSubTab);
    else if (tab === "whatsapp" && subTab) setWaSubTab(subTab as WhatsAppSubTab);
    else if (tab === "telegram" && subTab) setTgSubTab(subTab as TelegramSubTab);
  };

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1400px] px-8 py-8">
          <div className="space-y-6">
            <PageHeader
              title="Configuración"
              description="Ajustes operativos del sistema."
            />
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando configuración...
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
            <PageHeader
              title="Configuración"
              description="Ajustes operativos del sistema."
            />
            <EmptyState
              icon={Settings}
              title="Sin configuración disponible"
              description={loadError}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader
            title="Configuración"
            description="Ajustes operativos del sistema."
          />

          {readiness && !readiness.dashboard_unlocked && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold">Onboarding profesional pendiente</p>
                  <p className="mt-1 text-xs text-amber-800/80 dark:text-amber-200/80">
                    {readiness.summary}
                  </p>
                </div>
                <Link
                  href="/onboarding"
                  className="inline-flex items-center rounded-lg bg-foreground px-3 py-2 text-xs font-medium text-background transition hover:bg-foreground/80 active:translate-y-px"
                >
                  Abrir onboarding
                </Link>
              </div>
            </div>
          )}

          <Tabs
            value={activeTab}
            onValueChange={(v) => handleTabChange(v as TabId)}
          >
            <TabsList
              variant="line"
              className="mb-4 h-auto w-full justify-start border-b border-border"
            >
              {TABS.map((tab) => (
                <TabsTrigger
                  key={tab.id}
                  value={tab.id}
                  className="px-3 py-2 text-xs font-medium"
                >
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>

            <TabsContent value="setup">
              {setupData ? (
                <SetupChecklist data={setupData} onTabChange={handleTabChange} />
              ) : (
                <NoDataNotice />
              )}
            </TabsContent>

            <TabsContent value="identity">
              {opData ? (
                <BrandSection data={opData} onSaved={handleSavedOps} />
              ) : (
                <NoDataNotice />
              )}
            </TabsContent>

            <TabsContent value="email">
              {opData && mailData && credsData ? (
                <EmailSection
                  opData={opData}
                  mailData={mailData}
                  credsData={credsData}
                  subTab={emailSubTab}
                  onSubTabChange={setEmailSubTab}
                  onSavedOps={handleSavedOps}
                  onSavedCreds={handleSavedCreds}
                />
              ) : (
                <NoDataNotice />
              )}
            </TabsContent>

            <TabsContent value="whatsapp">
              {opData && waCredsData ? (
                <WhatsAppTabSection
                  waData={waCredsData}
                  opData={opData}
                  subTab={waSubTab}
                  onSubTabChange={setWaSubTab}
                  onSavedWa={handleSavedWACreds}
                  onSavedOps={handleSavedOps}
                />
              ) : (
                <NoDataNotice />
              )}
            </TabsContent>

            <TabsContent value="telegram">
              {opData && tgCredsData ? (
                <TelegramTabSection
                  tgData={tgCredsData}
                  opData={opData}
                  subTab={tgSubTab}
                  onSubTabChange={setTgSubTab}
                  onSavedTg={handleSavedTGCreds}
                  onSavedOps={handleSavedOps}
                />
              ) : (
                <NoDataNotice />
              )}
            </TabsContent>

            <TabsContent value="ai">
              {opData ? (
                <AutomationRulesSection data={opData} onSaved={handleSavedOps} />
              ) : (
                <NoDataNotice />
              )}
            </TabsContent>

            <TabsContent value="notifications">
              {opData ? (
                <NotificationsSection data={opData} onSaved={handleSavedOps} />
              ) : (
                <NoDataNotice />
              )}
            </TabsContent>

            <TabsContent value="data">
              {opData ? (
                <DataSection
                  opData={opData}
                  subTab={dataSubTab}
                  onSubTabChange={setDataSubTab}
                  onSavedOps={handleSavedOps}
                />
              ) : (
                <NoDataNotice />
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}

function NoDataNotice() {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 text-xs text-muted-foreground">
      <div className="flex items-center gap-2">
        <TriangleAlert className="h-4 w-4 text-amber-500" />
        No se pudieron cargar los datos para esta sección.
      </div>
    </div>
  );
}
