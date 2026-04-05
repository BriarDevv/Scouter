"use client";

import { useEffect, useState } from "react";
import { SectionHeader } from "@/components/shared/section-header";
import { StatCard } from "@/components/shared/stat-card";
import { SkeletonStatCard, SkeletonCard } from "@/components/shared/skeleton";
import { formatPercent } from "@/lib/formatters";
import {
  getAiHealth,
  getOutcomeAnalytics,
  getSignalCorrelations,
  getScoringRecommendations,
  getCorrectionsSummary,
  type AiHealthData,
  type ScoringRecommendation,
} from "@/lib/api/client";
import type { OutcomeAnalytics, SignalCorrelation, ReviewCorrectionSummary } from "@/types";
import {
  Brain, Activity, TrendingUp, AlertTriangle, CheckCircle,
  XCircle, Zap, Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";

const SIGNAL_COLORS: Record<string, string> = {
  no_website: "bg-red-500",
  instagram_only: "bg-purple-500",
  outdated_website: "bg-amber-500",
  no_ssl: "bg-orange-500",
  no_mobile_friendly: "bg-yellow-500",
  has_website: "bg-green-500",
};

export function AiScorePanel() {
  const [health, setHealth] = useState<AiHealthData | null>(null);
  const [outcomes, setOutcomes] = useState<OutcomeAnalytics | null>(null);
  const [signals, setSignals] = useState<SignalCorrelation[]>([]);
  const [corrections, setCorrections] = useState<ReviewCorrectionSummary[]>([]);
  const [recommendations, setRecommendations] = useState<ScoringRecommendation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getAiHealth().catch(() => null),
      getOutcomeAnalytics().catch(() => null),
      getSignalCorrelations().catch(() => []),
      getCorrectionsSummary(30).catch(() => []),
      getScoringRecommendations().catch(() => []),
    ]).then(([h, o, s, c, r]) => {
      setHealth(h);
      setOutcomes(o);
      setSignals(s as SignalCorrelation[]);
      setCorrections(c as ReviewCorrectionSummary[]);
      setRecommendations(r as ScoringRecommendation[]);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <SectionHeader title="AI Performance" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <SkeletonStatCard key={i} />)}
        </div>
        <SkeletonCard className="h-48" />
      </div>
    );
  }

  const totalOutcomes = (outcomes?.total_won ?? 0) + (outcomes?.total_lost ?? 0);
  const winRate = totalOutcomes > 0
    ? ((outcomes?.total_won ?? 0) / totalOutcomes)
    : 0;

  return (
    <div className="space-y-6">
      <SectionHeader title="AI Performance & Learning" />

      {/* Health Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Invocaciones IA (24h)"
          value={health?.invocations_24h ?? 0}
          icon={Zap}
        />
        <StatCard
          label="Approval Rate"
          value={formatPercent(health?.approval_rate ?? 0)}
          icon={CheckCircle}
        />
        <StatCard
          label="Fallback Rate"
          value={formatPercent(health?.fallback_rate ?? 0)}
          icon={AlertTriangle}
        />
        <StatCard
          label="Latencia Prom."
          value={health?.avg_latency_ms ? `${Math.round(health.avg_latency_ms)}ms` : "—"}
          icon={Activity}
        />
      </div>

      {/* Outcomes */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-foreground mb-4 font-heading flex items-center gap-2">
            <Trophy className="h-4 w-4" /> Outcomes
          </h3>
          <div className="flex items-center gap-6 mb-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-500">{outcomes?.total_won ?? 0}</div>
              <div className="text-xs text-muted-foreground">WON</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-500">{outcomes?.total_lost ?? 0}</div>
              <div className="text-xs text-muted-foreground">LOST</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-foreground">{formatPercent(winRate)}</div>
              <div className="text-xs text-muted-foreground">Win Rate</div>
            </div>
          </div>
          {totalOutcomes === 0 && (
            <p className="text-xs text-muted-foreground">
              Sin outcomes registrados. Marca leads como WON/LOST para activar el learning.
            </p>
          )}
          {(outcomes?.by_industry ?? []).length > 0 && (
            <div className="space-y-1 mt-2">
              <p className="text-xs font-medium text-muted-foreground">Por industria:</p>
              {outcomes!.by_industry.slice(0, 5).map((row) => (
                <div key={row.industry} className="flex justify-between text-xs">
                  <span className="text-foreground">{row.industry}</span>
                  <span>
                    <span className="text-green-500">{row.won}W</span>
                    {" / "}
                    <span className="text-red-500">{row.lost}L</span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Signal Correlations */}
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-foreground mb-4 font-heading flex items-center gap-2">
            <TrendingUp className="h-4 w-4" /> Signal Win Rates
          </h3>
          {signals.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Se necesitan 50+ outcomes para correlaciones de signals.
            </p>
          ) : (
            <div className="space-y-2">
              {signals.slice(0, 8).map((s) => (
                <div key={s.signal} className="flex items-center gap-2">
                  <div className={cn(
                    "h-2 w-2 rounded-full",
                    SIGNAL_COLORS[s.signal] ?? "bg-slate-400",
                  )} />
                  <span className="text-xs text-foreground flex-1 truncate">{s.signal}</span>
                  <div className="w-24 bg-muted rounded-full h-2">
                    <div
                      className="bg-green-500 rounded-full h-2"
                      style={{ width: `${Math.round(s.win_rate * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-mono text-muted-foreground w-10 text-right">
                    {formatPercent(s.win_rate)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Corrections & Recommendations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Review Corrections */}
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-foreground mb-4 font-heading flex items-center gap-2">
            <Shield className="h-4 w-4" /> Reviewer Corrections (30d)
          </h3>
          {corrections.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Sin correcciones registradas. El Reviewer genera feedback cuando revisa drafts y briefs.
            </p>
          ) : (
            <div className="space-y-2">
              {corrections.slice(0, 6).map((c) => (
                <div key={c.category} className="flex justify-between items-center">
                  <span className="text-xs text-foreground capitalize">{c.category}</span>
                  <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded">
                    {c.count}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Scoring Recommendations */}
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-foreground mb-4 font-heading flex items-center gap-2">
            <TrendingUp className="h-4 w-4" /> Scoring Recommendations
          </h3>
          {recommendations.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Se necesitan 50+ outcomes para generar recomendaciones de scoring.
            </p>
          ) : (
            <div className="space-y-2">
              {recommendations.slice(0, 5).map((r, i) => (
                <div key={i} className="rounded-lg bg-muted/50 p-2">
                  <p className="text-xs text-foreground">{r.message}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Confianza: {r.confidence}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Re-export Trophy for use in the page
import { Trophy } from "lucide-react";
