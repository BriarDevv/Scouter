"use client";

import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RuntimeMode } from "@/types";

interface RuntimeModePanelProps {
  currentMode: RuntimeMode;
  saving: boolean;
  onChange: (mode: RuntimeMode) => void;
}

export function RuntimeModePanel({ currentMode, saving, onChange }: RuntimeModePanelProps) {
  return (
    <div className="flex items-center justify-between border-b border-border px-5 py-2.5">
      <div className="flex items-center gap-2">
        <span className={cn(
          "h-2.5 w-2.5 rounded-full",
          currentMode === "safe" ? "bg-emerald-500" : currentMode === "assisted" ? "bg-amber-500" : "bg-red-500"
        )} />
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Modo Runtime
        </span>
      </div>
      <div className="flex items-center gap-1">
        {(["safe", "assisted", "auto"] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => onChange(mode)}
            disabled={saving}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition-all",
              currentMode === mode
                ? mode === "safe" ? "bg-emerald-600 text-white"
                  : mode === "assisted" ? "bg-amber-500 text-white"
                  : "bg-red-600 text-white"
                : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            {mode === "safe" ? "Seguro" : mode === "assisted" ? "Asistido" : "Auto"}
          </button>
        ))}
        {saving && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground ml-1" />}
      </div>
    </div>
  );
}
