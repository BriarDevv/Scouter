"use client";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { CredentialsSection } from "./credentials-section";
import { EmailRulesSection } from "./email-rules-section";
import { EmailSignatureSection } from "./email-signature-section";
import { MailIOSection } from "./mail-io-section";
import type { EmailSubTab } from "./types";
import type {
  MailCredentials,
  MailSettings,
  OperationalSettings,
} from "@/types";

interface EmailSectionProps {
  opData: OperationalSettings;
  mailData: MailSettings;
  credsData: MailCredentials;
  subTab: EmailSubTab;
  onSubTabChange: (tab: EmailSubTab) => void;
  onSavedOps: (updated: OperationalSettings) => void;
  onSavedCreds: (updated: MailCredentials) => void;
}

const SUB_TABS: { id: EmailSubTab; label: string }[] = [
  { id: "mail", label: "Salida y entrada" },
  { id: "credentials", label: "Credenciales SMTP / IMAP" },
  { id: "signature", label: "Firma" },
  { id: "rules", label: "Reglas" },
];

export function EmailSection({
  opData,
  mailData,
  credsData,
  subTab,
  onSubTabChange,
  onSavedOps,
  onSavedCreds,
}: EmailSectionProps) {
  return (
    <Tabs value={subTab} onValueChange={(v) => onSubTabChange(v as EmailSubTab)}>
      <TabsList className="mb-2 h-auto group-data-horizontal/tabs:h-auto w-full flex-wrap gap-1 rounded-xl border border-border bg-card p-1">
        {SUB_TABS.map((tab) => (
          <TabsTrigger
            key={tab.id}
            value={tab.id}
            className="h-auto rounded-md px-3 py-1 text-xs font-medium"
          >
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
      <TabsContent value="mail">
        <MailIOSection
          data={opData}
          mailData={mailData}
          onSaved={onSavedOps}
        />
      </TabsContent>
      <TabsContent value="credentials">
        <CredentialsSection data={credsData} onSaved={onSavedCreds} />
      </TabsContent>
      <TabsContent value="signature">
        <EmailSignatureSection data={opData} onSaved={onSavedOps} />
      </TabsContent>
      <TabsContent value="rules">
        <EmailRulesSection data={opData} onSaved={onSavedOps} />
      </TabsContent>
    </Tabs>
  );
}
