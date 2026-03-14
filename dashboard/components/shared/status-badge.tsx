import { cn } from "@/lib/utils";
import {
  DRAFT_STATUS_CONFIG,
  INBOUND_CLASSIFICATION_STATUS_CONFIG,
  INBOUND_REPLY_LABEL_CONFIG,
  QUALITY_CONFIG,
  STATUS_CONFIG,
} from "@/lib/constants";
import type {
  DraftStatus,
  InboundClassificationLabel,
  InboundClassificationStatus,
  LeadQuality,
  LeadStatus,
} from "@/types";

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
  if (score === null) return <span className="text-xs text-muted-foreground">—</span>;
  const level = score >= 60 ? "high" : score >= 30 ? "medium" : "low";
  const styles = {
    high: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300",
    medium: "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300",
    low: "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300",
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

export function InboundClassificationStatusBadge({
  status,
}: {
  status: InboundClassificationStatus;
}) {
  const config = INBOUND_CLASSIFICATION_STATUS_CONFIG[status];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.bg,
        config.color
      )}
    >
      {config.label}
    </span>
  );
}

export function InboundReplyLabelBadge({
  label,
}: {
  label: InboundClassificationLabel | null;
}) {
  if (!label) {
    return (
      <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
        Sin label
      </span>
    );
  }
  const config = INBOUND_REPLY_LABEL_CONFIG[label];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.bg,
        config.color
      )}
    >
      {config.label}
    </span>
  );
}
