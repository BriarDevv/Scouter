"use client";

import { FeatureToggleList, type FeatureToggle } from "@/components/dashboard/feature-toggle-list";
import type { OperationalSettings } from "@/types";

interface FeatureTogglesProps {
  title: string;
  features: FeatureToggle[];
  settings: OperationalSettings | null;
  loading: boolean;
  savingKey: string | null;
  onToggle: (key: keyof OperationalSettings, value: boolean) => void;
  warningMessage?: string;
}

export function FeatureToggles({
  title,
  features,
  settings,
  loading,
  savingKey,
  onToggle,
  warningMessage,
}: FeatureTogglesProps) {
  return (
    <div className="p-4 space-y-2">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </p>
      <FeatureToggleList
        features={features}
        settings={settings}
        loading={loading}
        savingKey={savingKey}
        accentColor="emerald"
        onToggle={onToggle}
        warningMessage={warningMessage}
      />
    </div>
  );
}
