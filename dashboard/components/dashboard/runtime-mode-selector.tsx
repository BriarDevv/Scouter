"use client";

import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RuntimeMode } from "@/types";

interface RuntimeModeSelectorProps {
  currentMode: RuntimeMode;
  saving: boolean;
  onChange: (mode: RuntimeMode) => void;
}

export function RuntimeModeSelector({ currentMode, saving, onChange }: RuntimeModeSelectorProps) {
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Modo Runtime</p>
      <div className="flex gap-1">
        {(["safe", "assisted", "auto"] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => void onChange(mode)}
            disabled={saving}
            title={mode === "safe" ? "Maxima seguridad" : mode === "assisted" ? "Pipeline automatico" : "Full auto"}
            className={cn(
              "flex-1 rounded-lg py-2 text-xs font-bold uppercase tracking-wider transition-all",
              currentMode === mode
                ? mode === "safe" ? "bg-emerald-600 text-white"
                  : mode === "assisted" ? "bg-amber-500 text-white"
                  : "bg-red-600 text-white"
                : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            {mode === "safe" ? "Safe" : mode === "assisted" ? "Assist" : "Auto"}
          </button>
        ))}
      </div>
      {saving && (
        <div className="flex items-center gap-1.5">
          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
          <span className="text-[10px] text-muted-foreground">Guardando...</span>
        </div>
      )}
    </div>
  );
}
