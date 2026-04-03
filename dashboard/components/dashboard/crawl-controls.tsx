"use client";

import { Loader2, Search, Square } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TerritoryWithStats } from "@/types";

interface CrawlControlsProps {
  crawlStatus: "idle" | "running" | "done" | "error";
  crawlProgress: string | null;
  territories: TerritoryWithStats[];
  selectedTerritoryId: string;
  celeryOk: boolean;
  onTerritoryChange: (id: string) => void;
  onStart: () => void;
  onStop: () => void;
}

export function CrawlControls({
  crawlStatus,
  crawlProgress,
  territories,
  selectedTerritoryId,
  celeryOk,
  onTerritoryChange,
  onStart,
  onStop,
}: CrawlControlsProps) {
  return (
    <div className="pt-1 space-y-1.5">
      {territories.length > 0 && (
        <select
          value={selectedTerritoryId}
          onChange={(e) => onTerritoryChange(e.target.value)}
          disabled={crawlStatus === "running"}
          className="w-full appearance-none rounded-lg border border-border bg-muted px-2.5 py-1.5 text-xs text-foreground outline-none disabled:opacity-50"
        >
          {territories.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} ({t.cities?.length ?? 0} ciudades)
            </option>
          ))}
        </select>
      )}
      {crawlStatus !== "running" ? (
        <button
          onClick={onStart}
          disabled={!celeryOk || !selectedTerritoryId}
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all",
            celeryOk && selectedTerritoryId
              ? "bg-emerald-600 text-white hover:bg-emerald-700 active:scale-[0.98]"
              : "bg-muted text-muted-foreground cursor-not-allowed"
          )}
        >
          <Search className="h-4 w-4" />
          Iniciar Crawl
        </button>
      ) : (
        <button
          onClick={onStop}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 active:scale-[0.98] transition-all"
        >
          <Square className="h-4 w-4" />
          Detener Crawl
        </button>
      )}
      {crawlProgress && (
        <p className={cn(
          "text-[10px] text-center",
          crawlStatus === "running" ? "text-violet-500" : crawlStatus === "done" ? "text-emerald-500" : "text-red-500"
        )}>
          {crawlStatus === "running" && <Loader2 className="inline h-3 w-3 animate-spin mr-1" />}
          {crawlProgress}
        </p>
      )}
    </div>
  );
}
