"use client";

import Link from "next/link";
import { useState } from "react";
import { Loader2, Settings, TriangleAlert } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
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
import { PricingSection } from "@/components/settings/pricing-section";
import type { WhatsAppCredentials } from "@/components/settings/whatsapp-section";
import type { TelegramCredentials } from "@/lib/api/client";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("setup");

  const { data: mailData, isLoading: mailLoading, mutate: mutateMail } = useApi<MailSettings>("/settings/mail");
  const { data: opData, isLoading: opLoading, mutate: mutateOp } = useApi<OperationalSettings>("/settings/operational");
  const { data: credsData, mutate: mutateCreds } = useApi<MailCredentials>("/settings/mail-credentials");
  const { data: setupData, mutate: mutateSetup } = useApi<SetupStatus>("/settings/setup-status");
  const { data: readiness, mutate: mutateReadiness } = useApi<SetupReadiness>("/setup/readiness");
  const { data: waCredsData, mutate: mutateWaCreds } = useApi<WhatsAppCredentials>("/settings/whatsapp-credentials");
  const { data: tgCredsData, mutate: mutateTgCreds } = useApi<TelegramCredentials>("/settings/telegram-credentials");

  const loading = mailLoading || opLoading;
  const loadError = !loading && !mailData && !opData ? "No se pudo conectar con el backend." : null;

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

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1400px] px-8 py-8">
          <div className="space-y-6">
            <PageHeader title="Configuracion" description="Ajustes operativos del sistema." />
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando configuracion...
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
            <PageHeader title="Configuracion" description="Ajustes operativos del sistema." />
            <EmptyState icon={Settings} title="Sin configuracion disponible" description={loadError} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader title="Configuracion" description="Ajustes operativos del sistema." />

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
                  className="inline-flex items-center rounded-xl bg-foreground px-3 py-2 text-xs font-medium text-background transition hover:bg-foreground/80"
                >
                  Abrir onboarding
                </Link>
              </div>
            </div>
          )}

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
        <TabsContent value="pricing">
          {opData ? (
            <PricingSection data={opData} onSaved={handleSavedOps} />
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
          Ultima actualizacion: <RelativeTime date={opData.updated_at} />
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
        No se pudieron cargar los datos para esta seccion.
      </div>
    </div>
  );
}
