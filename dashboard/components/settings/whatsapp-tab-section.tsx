"use client";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  HermesWhatsAppSection,
  KapsoOutreachSection,
  WhatsAppSection,
} from "./whatsapp-section";
import type { WhatsAppCredentials } from "./whatsapp-section";
import type { WhatsAppSubTab } from "./types";
import type { OperationalSettings } from "@/types";

interface WhatsAppTabSectionProps {
  waData: WhatsAppCredentials;
  opData: OperationalSettings;
  subTab: WhatsAppSubTab;
  onSubTabChange: (tab: WhatsAppSubTab) => void;
  onSavedWa: (updated: WhatsAppCredentials) => void;
  onSavedOps: (updated: OperationalSettings) => void;
}

const SUB_TABS: { id: WhatsAppSubTab; label: string }[] = [
  { id: "alerts", label: "Alertas (CallMeBot)" },
  { id: "outreach", label: "Outreach (Kapso)" },
  { id: "agent", label: "Agente Mote" },
];

export function WhatsAppTabSection({
  waData,
  opData,
  subTab,
  onSubTabChange,
  onSavedWa,
  onSavedOps,
}: WhatsAppTabSectionProps) {
  return (
    <Tabs value={subTab} onValueChange={(v) => onSubTabChange(v as WhatsAppSubTab)}>
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
      <TabsContent value="alerts">
        <WhatsAppSection data={waData} onSaved={onSavedWa} />
      </TabsContent>
      <TabsContent value="outreach">
        <KapsoOutreachSection data={opData} onSaved={onSavedOps} />
      </TabsContent>
      <TabsContent value="agent">
        <HermesWhatsAppSection data={opData} onSaved={onSavedOps} />
      </TabsContent>
    </Tabs>
  );
}
