"use client";

import { useEffect, useState } from "react";
import {
  getBatchReviews,
  getBatchReviewDetail,
  triggerBatchReview,
  approveProposal,
  rejectProposal,
  applyProposal,
  type BatchReviewSummary,
  type BatchReviewDetail,
} from "@/lib/api/client";
import {
  Brain, ChevronDown, ChevronRight, Check, X, Play,
  Loader2, AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";

const IMPACT_STYLES: Record<string, string> = {
  high: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  low: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "text-green-600 dark:text-green-400",
  medium: "text-amber-600 dark:text-amber-400",
  low: "text-red-600 dark:text-red-400",
};

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
  approved: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  applied: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  rejected: "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
};

export function BatchReviewsSection() {
  const [reviews, setReviews] = useState<BatchReviewSummary[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<BatchReviewDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadReviews = async () => {
    try {
      const data = await getBatchReviews(10);
      setReviews(data);
    } catch (err) { console.error("batch_reviews_fetch_failed", err); }
    setLoading(false);
  };

  useEffect(() => { loadReviews(); }, []);

  const toggleExpand = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(id);
    try {
      const d = await getBatchReviewDetail(id);
      setDetail(d);
    } catch (err) { console.error("batch_review_detail_fetch_failed", err); setDetail(null); }
  };

  const handleAction = async (proposalId: string, action: "approve" | "reject" | "apply") => {
    setActionLoading(proposalId);
    try {
      if (action === "approve") await approveProposal(proposalId);
      else if (action === "reject") await rejectProposal(proposalId);
      else await applyProposal(proposalId);
      // Refresh detail
      if (expandedId) {
        const d = await getBatchReviewDetail(expandedId);
        setDetail(d);
      }
      await loadReviews();
    } catch (err) { console.error("batch_review_action_failed", err); }
    setActionLoading(null);
  };

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          <h3 className="text-sm font-medium">Batch Reviews (Reuniones IA)</h3>
        </div>
        <button
          onClick={async () => {
            setGenerating(true);
            try { await triggerBatchReview(); await loadReviews(); } catch (err) { console.error("batch_review_trigger_failed", err); }
            setGenerating(false);
          }}
          disabled={generating}
          className="text-xs px-3 py-1 rounded-md bg-indigo-100 text-indigo-700 hover:bg-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300 dark:hover:bg-indigo-900/50 disabled:opacity-50"
        >
          {generating ? "Generando..." : "Generar ahora"}
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-4"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
      ) : reviews.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin batch reviews. Se generan automaticamente cada 25 leads o 10 HIGH leads procesados.</p>
      ) : (
        <div className="space-y-2">
          {reviews.map((r) => (
            <div key={r.id} className="rounded-lg border border-border/50">
              <button
                onClick={() => toggleExpand(r.id)}
                className="w-full flex items-center justify-between p-3 text-left hover:bg-muted/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {expandedId === r.id ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                  <span className="text-xs font-medium">{r.trigger_reason}</span>
                  <span className="text-xs text-muted-foreground">{r.batch_size} leads</span>
                  <span className={cn("text-xs px-1.5 py-0.5 rounded", r.status === "completed" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" : "bg-red-100 text-red-700")}>
                    {r.status}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {r.proposals_pending > 0 && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300 font-medium">
                      {r.proposals_pending} pendientes
                    </span>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {r.created_at ? new Date(r.created_at).toLocaleDateString("es-AR") : ""}
                  </span>
                </div>
              </button>

              {expandedId === r.id && detail && (
                <div className="border-t border-border/50 p-3 space-y-3">
                  {/* Strategy Brief */}
                  {detail.strategy_brief && (
                    <div className="rounded-lg bg-muted/30 p-3">
                      <p className="text-xs font-medium text-foreground mb-1">Strategy Brief</p>
                      <p className="text-xs text-muted-foreground whitespace-pre-line line-clamp-6">{detail.strategy_brief}</p>
                    </div>
                  )}

                  {detail.reviewer_notes && (
                    <p className="text-xs text-muted-foreground"><strong>Reviewer:</strong> {detail.reviewer_notes}</p>
                  )}

                  {/* Proposals */}
                  {detail.proposals.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-foreground mb-2">Proposals ({detail.proposals.length})</p>
                      <div className="space-y-2">
                        {detail.proposals.map((p) => (
                          <div key={p.id} className="rounded-lg border border-border/30 p-2.5">
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className={cn("text-xs px-1.5 py-0.5 rounded font-medium", IMPACT_STYLES[p.impact] || IMPACT_STYLES.medium)}>
                                    {p.impact}
                                  </span>
                                  <span className={cn("text-xs font-medium", CONFIDENCE_STYLES[p.confidence] || "")}>
                                    conf: {p.confidence}
                                  </span>
                                  <span className="text-xs text-muted-foreground capitalize">{p.category}</span>
                                  <span className={cn("text-xs px-1.5 py-0.5 rounded", STATUS_STYLES[p.status] || "")}>
                                    {p.status}
                                  </span>
                                </div>
                                <p className="text-xs text-foreground">{p.description}</p>
                                {p.evidence_summary && (
                                  <p className="text-xs text-muted-foreground mt-1">Evidencia: {p.evidence_summary}</p>
                                )}
                              </div>

                              {p.status === "pending" && (
                                <div className="flex gap-1 shrink-0">
                                  <button
                                    onClick={() => handleAction(p.id, "approve")}
                                    disabled={actionLoading === p.id}
                                    className="p-1 rounded hover:bg-green-100 dark:hover:bg-green-900/30 text-green-600"
                                    title="Aprobar"
                                  >
                                    <Check className="h-3.5 w-3.5" />
                                  </button>
                                  <button
                                    onClick={() => handleAction(p.id, "reject")}
                                    disabled={actionLoading === p.id}
                                    className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600"
                                    title="Rechazar"
                                  >
                                    <X className="h-3.5 w-3.5" />
                                  </button>
                                </div>
                              )}

                              {p.status === "approved" && (
                                <button
                                  onClick={() => handleAction(p.id, "apply")}
                                  disabled={actionLoading === p.id}
                                  className="p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-600"
                                  title="Aplicar"
                                >
                                  <Play className="h-3.5 w-3.5" />
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
