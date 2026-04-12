"use client";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { HermesTelegramSection, TelegramSection } from "./telegram-section";
import type { TelegramCredentials } from "@/lib/api/client";
import type { TelegramSubTab } from "./types";
import type { OperationalSettings } from "@/types";

interface TelegramTabSectionProps {
  tgData: TelegramCredentials;
  opData: OperationalSettings;
  subTab: TelegramSubTab;
  onSubTabChange: (tab: TelegramSubTab) => void;
  onSavedTg: (updated: TelegramCredentials) => void;
  onSavedOps: (updated: OperationalSettings) => void;
}

const SUB_TABS: { id: TelegramSubTab; label: string }[] = [
  { id: "bot", label: "Bot" },
  { id: "agent", label: "Agente Mote" },
];

export function TelegramTabSection({
  tgData,
  opData,
  subTab,
  onSubTabChange,
  onSavedTg,
  onSavedOps,
}: TelegramTabSectionProps) {
  return (
    <Tabs value={subTab} onValueChange={(v) => onSubTabChange(v as TelegramSubTab)}>
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
      <TabsContent value="bot">
        <TelegramSection data={tgData} onSaved={onSavedTg} />
      </TabsContent>
      <TabsContent value="agent">
        <HermesTelegramSection data={opData} onSaved={onSavedOps} />
      </TabsContent>
    </Tabs>
  );
}
