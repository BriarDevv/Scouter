import { cn } from "@/lib/utils";
import { STATUS_CONFIG, QUALITY_CONFIG, DRAFT_STATUS_CONFIG } from "@/lib/constants";
import type { LeadStatus, LeadQuality, DraftStatus } from "@/types";

export function StatusBadge({ status }: { status: LeadStatus }) {
  const config = STATUS_CONFIG[status];
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", config.bg, config.color)}>
      {config.label}
    </span>
  );
}

export function QualityBadge({ quality }: { quality: LeadQuality }) {
  const config = QUALITY_CONFIG[quality];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium", config.bg, config.color)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dot)} />
      {config.label}
    </span>
  );
}

export function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-slate-400">—</span>;
  const level = score >= 60 ? "high" : score >= 30 ? "medium" : "low";
  const styles = {
    high: "bg-emerald-50 text-emerald-700",
    medium: "bg-amber-50 text-amber-700",
    low: "bg-red-50 text-red-700",
  };
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold font-data", styles[level])}>
      {score.toFixed(0)}
    </span>
  );
}

export function DraftStatusBadge({ status }: { status: DraftStatus }) {
  const config = DRAFT_STATUS_CONFIG[status];
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", config.bg, config.color)}>
      {config.label}
    </span>
  );
}
