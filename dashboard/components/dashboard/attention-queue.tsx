"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch, getBatchReviews, type BatchReviewSummary } from "@/lib/api/client";
import { useVisibleInterval } from "@/lib/hooks/use-visible-interval";
import { AlertTriangle, FileWarning, MessageSquare, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface AttentionItem {
  type: "proposal" | "stuck_pipeline" | "failed_pipeline" | "conversation";
  label: string;
  detail: string;
  count: number;
  href?: string;
}

export function AttentionQueue() {
  const [items, setItems] = useState<AttentionItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const attention: AttentionItem[] = [];

    // Pending proposals
    try {
      const reviews = await getBatchReviews(20);
      const pending = reviews.reduce((sum, r) => sum + r.proposals_pending, 0);
      if (pending > 0) {
        attention.push({
          type: "proposal",
          label: "Proposals pendientes",
          detail: "Batch review proposals esperando aprobacion",
          count: pending,
        });
      }
    } catch (err) { console.error("attention_queue_proposals_fetch_failed", err); }

    // Stuck pipelines
    try {
      const runs = await apiFetch<Array<{ status: string; finished_at: string | null }>>("/pipelines/runs?page_size=50");
      const stuck = (Array.isArray(runs) ? runs : []).filter(
        (r) => r.status === "running" && !r.finished_at
      ).length;
      const failed = (Array.isArray(runs) ? runs : []).filter(
        (r) => r.status === "failed"
      ).length;
      if (stuck > 0) {
        attention.push({
          type: "stuck_pipeline",
          label: "Pipelines trabados",
          detail: "Pipeline runs stuck — necesitan resume",
          count: stuck,
        });
      }
      if (failed > 0) {
        attention.push({
          type: "failed_pipeline",
          label: "Pipelines fallidos",
          detail: "Pipeline runs que terminaron con error",
          count: failed,
        });
      }
    } catch (err) { console.error("attention_queue_pipelines_fetch_failed", err); }

    // Active conversations needing attention
    try {
      const convos = await apiFetch<Array<{ status: string }>>("/ai-office/conversations?limit=50");
      const active = (Array.isArray(convos) ? convos : []).filter(
        (c) => c.status === "active"
      ).length;
      if (active > 0) {
        attention.push({
          type: "conversation",
          label: "Conversaciones activas",
          detail: "Mote conversations que podrian necesitar takeover",
          count: active,
        });
      }
    } catch (err) { console.error("attention_queue_conversations_fetch_failed", err); }

    setItems(attention);
    setLoading(false);
  }, []);

  useVisibleInterval(load, 30_000);

  if (loading || items.length === 0) return null;

  const ICONS: Record<string, typeof AlertTriangle> = {
    proposal: Zap,
    stuck_pipeline: AlertTriangle,
    failed_pipeline: FileWarning,
    conversation: MessageSquare,
  };

  const COLORS: Record<string, string> = {
    proposal: "border-amber-500/30 bg-amber-500/5",
    stuck_pipeline: "border-red-500/30 bg-red-500/5",
    failed_pipeline: "border-red-500/20 bg-red-500/5",
    conversation: "border-blue-500/30 bg-blue-500/5",
  };

  return (
    <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
        <h3 className="text-sm font-medium">Necesita atencion ({items.reduce((s, i) => s + i.count, 0)})</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {items.map((item) => {
          const Icon = ICONS[item.type] || AlertTriangle;
          return (
            <div
              key={item.type}
              className={cn("rounded-lg border p-3 flex items-center gap-3", COLORS[item.type])}
            >
              <Icon className="h-4 w-4 shrink-0 text-foreground/70" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-foreground">{item.label}</p>
                <p className="text-xs text-muted-foreground">{item.detail}</p>
              </div>
              <span className="text-lg font-bold text-foreground">{item.count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
