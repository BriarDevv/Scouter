"use client";

import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { OperationalSettings } from "@/types";

export interface FeatureToggle {
  key: keyof OperationalSettings;
  label: string;
  hint: string;
  icon: React.ElementType;
  category: "ia" | "mail" | "whatsapp";
  dependsOn?: keyof OperationalSettings;
}

interface FeatureToggleListProps {
  features: FeatureToggle[];
  settings: OperationalSettings | null;
  loading: boolean;
  savingKey: string | null;
  accentColor: "violet" | "emerald";
  onToggle: (key: keyof OperationalSettings, value: boolean) => void;
  warningMessage?: string;
}

export function FeatureToggleList({
  features,
  settings,
  loading,
  savingKey,
  accentColor,
  onToggle,
  warningMessage,
}: FeatureToggleListProps) {
  const pending = loading || !settings;

  const colorEnabled = accentColor === "violet"
    ? "bg-muted dark:bg-muted"
    : "bg-emerald-50 dark:bg-emerald-950/30";

  const iconEnabled = accentColor === "violet"
    ? "text-foreground dark:text-foreground"
    : "text-emerald-600 dark:text-emerald-400";

  const toggleBg = accentColor === "violet" ? "bg-foreground" : "bg-emerald-600";

  return (
    <div className="space-y-1">
      {features.map((feat) => {
        const enabled = pending ? false : Boolean(settings[feat.key]);
        const saving = savingKey === feat.key;
        const depDisabled = feat.dependsOn && settings && !settings[feat.dependsOn];

        return (
          <button
            key={feat.key}
            onClick={() => onToggle(feat.key, !enabled)}
            disabled={pending || saving || Boolean(depDisabled)}
            className={cn(
              "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-all",
              enabled ? colorEnabled : "bg-muted/30 hover:bg-muted/50",
              depDisabled && "opacity-40 cursor-not-allowed"
            )}
          >
            <feat.icon className={cn(
              "h-4 w-4 flex-shrink-0",
              enabled ? iconEnabled : "text-muted-foreground"
            )} />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-foreground">{feat.label}</p>
              <p className="text-[10px] text-muted-foreground truncate">{feat.hint}</p>
            </div>
            <div className={cn(
              "flex h-5 w-9 flex-shrink-0 items-center rounded-full px-0.5 transition-colors",
              enabled ? toggleBg : "bg-muted-foreground/30"
            )}>
              <div className={cn(
                "h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
                enabled ? "translate-x-4" : "translate-x-0"
              )} />
            </div>
            {saving && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
          </button>
        );
      })}

      {warningMessage && (
        <p className="text-[10px] text-amber-500 px-3 pt-1">
          {warningMessage}
        </p>
      )}
    </div>
  );
}
