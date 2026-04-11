"use client";

import { Loader2, Search, Square } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
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
        <Button
          variant="success"
          onClick={onStart}
          disabled={!celeryOk || !selectedTerritoryId}
          size="lg"
          className="w-full rounded-xl"
        >
          <Search className="h-4 w-4" />
          Iniciar Crawl
        </Button>
      ) : (
        <Button
          variant="destructive-solid"
          onClick={onStop}
          size="lg"
          className="w-full rounded-xl"
        >
          <Square className="h-4 w-4" />
          Detener Crawl
        </Button>
      )}
      {crawlProgress && (
        <p className={cn(
          "text-[10px] text-center",
          crawlStatus === "running" ? "text-foreground" : crawlStatus === "done" ? "text-emerald-500" : "text-red-500"
        )}>
          {crawlStatus === "running" && <Loader2 className="inline h-3 w-3 animate-spin mr-1" />}
          {crawlProgress}
        </p>
      )}
    </div>
  );
}
