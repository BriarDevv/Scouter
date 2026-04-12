"use client";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { CrawlersSection } from "./crawlers-section";
import { PricingSection } from "./pricing-section";
import { TerritoriesSection } from "./territories-section";
import type { DataSubTab } from "./types";
import type { OperationalSettings } from "@/types";

interface DataSectionProps {
  opData: OperationalSettings;
  subTab: DataSubTab;
  onSubTabChange: (tab: DataSubTab) => void;
  onSavedOps: (updated: OperationalSettings) => void;
}

const SUB_TABS: { id: DataSubTab; label: string }[] = [
  { id: "territories", label: "Territorios" },
  { id: "crawlers", label: "Crawlers" },
  { id: "pricing", label: "Matriz de precios" },
];

export function DataSection({
  opData,
  subTab,
  onSubTabChange,
  onSavedOps,
}: DataSectionProps) {
  return (
    <Tabs value={subTab} onValueChange={(v) => onSubTabChange(v as DataSubTab)}>
      <TabsList className="mb-2 h-auto group-data-horizontal/tabs:h-auto w-full flex-wrap gap-1 rounded-xl border border-border bg-card p-1">
        {SUB_TABS.map((tab) => (
          <TabsTrigger
            key={tab.id}
            value={tab.id}
            className="h-auto rounded-lg px-4 py-2 text-xs font-medium"
          >
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
      <TabsContent value="territories">
        <TerritoriesSection />
      </TabsContent>
      <TabsContent value="crawlers">
        <CrawlersSection />
      </TabsContent>
      <TabsContent value="pricing">
        <PricingSection data={opData} onSaved={onSavedOps} />
      </TabsContent>
    </Tabs>
  );
}
