"use client";

import { useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { AiHealthCard } from "@/components/dashboard/ai-health-card";
import { TopCorrections } from "@/components/dashboard/top-corrections";
import {
  Brain,
  Search,
  Sparkles,
  CheckCircle,
  Circle,
  Zap,
  Clock,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";
import {
  generateWeeklyReport,
  type OutboundConversation,
  type WeeklyReportData,
} from "@/lib/api/client";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import { BatchReviewsSection } from "@/components/ai-office/batch-reviews-section";
import { PipelineRunsSection } from "@/components/ai-office/pipeline-runs-section";
import { AttentionQueue } from "@/components/dashboard/attention-queue";
import { MessageSquare, FileText } from "lucide-react";
import type { AgentInfo, AiOfficeStatus, DecisionRecord, InvestigationRecord } from "@/types";

const AGENT_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  mote: Brain,
  scout: Search,
  executor: Sparkles,
  reviewer: CheckCircle,
};

const AGENT_COLOR_CLASSES: Record<string, { border: string; bg: string; icon: string }> = {
  mote:     { border: "border-violet-100 dark:border-violet-900/30", bg: "bg-violet-50/30 dark:bg-violet-950/20",   icon: "text-violet-600 dark:text-violet-400" },
  scout:    { border: "border-cyan-100 dark:border-cyan-900/30",     bg: "bg-cyan-50/30 dark:bg-cyan-950/20",       icon: "text-cyan-600 dark:text-cyan-400" },
  executor: { border: "border-blue-100 dark:border-blue-900/30",     bg: "bg-blue-50/30 dark:bg-blue-950/20",       icon: "text-blue-600 dark:text-blue-400" },
  reviewer: { border: "border-emerald-100 dark:border-emerald-900/30", bg: "bg-emerald-50/30 dark:bg-emerald-950/20", icon: "text-emerald-600 dark:text-emerald-400" },
};

const STATUS_DOT: Record<string, string> = {
  online: "text-emerald-500",
  active: "text-emerald-500",
  idle: "text-gray-400",
};

export default function AiOfficePage() {
  const swrOpts = { refreshInterval: 10_000 };
  const { data: status, isLoading: statusLoading } = useApi<AiOfficeStatus>("/ai-office/status", swrOpts);
  const { data: decisions } = useApi<DecisionRecord[]>("/ai-office/decisions?limit=15", swrOpts);
  const { data: investigations } = useApi<InvestigationRecord[]>("/ai-office/investigations?limit=5", swrOpts);
  const { data: conversations } = useApi<OutboundConversation[]>("/ai-office/conversations?limit=10", swrOpts);
  const { data: weeklyReports, mutate: mutateReports } = useApi<WeeklyReportData[]>("/ai-office/weekly-reports?limit=3", swrOpts);
  const [generatingReport, setGeneratingReport] = useState(false);
  const loading = statusLoading;

  return (
    <div className="flex-1 overflow-y-auto">
    <div className="mx-auto max-w-[1400px] px-8 py-8">
    <div className="space-y-6">
      <PageHeader
        title="AI Office"
        description="Estado del equipo de inteligencia artificial de Scouter"
      />

      {/* Attention Queue */}
      <AttentionQueue />

      {/* Agent Status Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {status
          ? (["mote", "scout", "executor", "reviewer"] as const).map((key) => {
              const agent = status.agents[key];
              const Icon = AGENT_ICONS[key];
              return (
                <AgentCard key={key} agent={agent} agentKey={key} Icon={Icon} colorClasses={AGENT_COLOR_CLASSES[key]} />
              );
            })
          : Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="rounded-xl border border-border bg-card p-4 animate-pulse h-32" />
            ))}
      </div>

      {/* Outcomes + Health Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <h3 className="text-sm font-medium">Outcomes</h3>
          </div>
          <div className="flex gap-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                {status?.outcomes.total_won ?? "—"}
              </p>
              <p className="text-xs text-muted-foreground">WON</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                {status?.outcomes.total_lost ?? "—"}
              </p>
              <p className="text-xs text-muted-foreground">LOST</p>
            </div>
            {status && (status.outcomes.total_won + status.outcomes.total_lost > 0) && (
              <div className="text-center">
                <p className="text-2xl font-bold text-foreground">
                  {Math.round(
                    (status.outcomes.total_won /
                      (status.outcomes.total_won + status.outcomes.total_lost)) *
                      100
                  )}%
                </p>
                <p className="text-xs text-muted-foreground">Win Rate</p>
              </div>
            )}
          </div>
        </div>
        <AiHealthCard />
        <TopCorrections />
      </div>

      {/* Scout Investigations */}
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Search className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
          <h3 className="text-sm font-medium">Investigaciones recientes de Scout</h3>
        </div>
        {(investigations ?? []).length > 0 ? (
          <div className="space-y-2">
            {(investigations ?? []).map((inv) => (
              <div key={inv.id} className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/20 p-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">
                    Lead {inv.lead_id.slice(0, 8)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {inv.pages_visited?.length || 0} paginas · {inv.loops_used} loops · {(inv.duration_ms / 1000).toFixed(1)}s
                  </p>
                  {Boolean(inv.findings?.opportunity) && (
                    <p className="text-xs text-foreground/70 mt-1 truncate">
                      {String(inv.findings.opportunity)}
                    </p>
                  )}
                </div>
                {inv.error ? (
                  <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                ) : (
                  <CheckCircle className="h-4 w-4 text-emerald-500 shrink-0" />
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Sin investigaciones recientes.</p>
        )}
      </div>

      {/* Mote Conversations */}
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <MessageSquare className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          <h3 className="text-sm font-medium">Conversaciones Activas (Mote)</h3>
        </div>
        {(conversations ?? []).length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="pb-2 pr-3">Lead</th>
                  <th className="pb-2 pr-3">Canal</th>
                  <th className="pb-2 pr-3">Estado</th>
                  <th className="pb-2 pr-3">Mensajes</th>
                  <th className="pb-2">Fecha</th>
                </tr>
              </thead>
              <tbody>
                {(conversations ?? []).map((c) => (
                  <tr key={c.id} className="border-b border-border/30 last:border-0">
                    <td className="py-2 pr-3 font-medium truncate max-w-[200px]">{c.lead_name || c.lead_id.slice(0, 8)}</td>
                    <td className="py-2 pr-3">
                      <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                        {c.channel}
                      </span>
                    </td>
                    <td className="py-2 pr-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        c.status === "active" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" :
                        c.status === "closed" ? "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300" :
                        "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300"
                      }`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-xs text-muted-foreground">{c.message_count}</td>
                    <td className="py-2 text-xs text-muted-foreground">
                      {new Date(c.created_at).toLocaleDateString("es-AR")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Sin conversaciones de outreach activas.</p>
        )}
      </div>

      {/* Weekly Reports */}
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <h3 className="text-sm font-medium">Reportes Semanales</h3>
          </div>
          <button
            onClick={async () => {
              setGeneratingReport(true);
              try {
                const report = await generateWeeklyReport();
                mutateReports((prev) => prev ? [report, ...prev] : [report], false);
              } catch (err) { console.error("weekly_report_generation_failed", err); }
              setGeneratingReport(false);
            }}
            disabled={generatingReport}
            className="text-xs px-3 py-1 rounded-md bg-amber-100 text-amber-700 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:hover:bg-amber-900/50 disabled:opacity-50"
          >
            {generatingReport ? "Generando..." : "Generar ahora"}
          </button>
        </div>
        {(weeklyReports ?? []).length > 0 ? (
          <div className="space-y-3">
            {(weeklyReports ?? []).map((r) => (
              <div key={r.id} className="rounded-lg border border-border/50 p-3">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-medium text-foreground">
                    Semana del {new Date(r.week_start).toLocaleDateString("es-AR")}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(r.created_at).toLocaleDateString("es-AR")}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground whitespace-pre-line line-clamp-4">
                  {r.synthesis_text || "Sin síntesis disponible."}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Sin reportes semanales. Genera uno manualmente o esperá al próximo domingo.</p>
        )}
      </div>

      {/* Batch Reviews */}
      <BatchReviewsSection />

      {/* Pipeline Runs */}
      <PipelineRunsSection />

      {/* Decision Log */}
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Zap className="h-4 w-4 text-violet-600 dark:text-violet-400" />
          <h3 className="text-sm font-medium">Decisiones recientes</h3>
        </div>
        {(decisions ?? []).length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="pb-2 pr-3">Funcion</th>
                  <th className="pb-2 pr-3">Rol</th>
                  <th className="pb-2 pr-3">Modelo</th>
                  <th className="pb-2 pr-3">Estado</th>
                  <th className="pb-2 pr-3">Latencia</th>
                  <th className="pb-2">Prompt</th>
                </tr>
              </thead>
              <tbody>
                {(decisions ?? []).map((d) => (
                  <tr key={d.id} className="border-b border-border/30 last:border-0">
                    <td className="py-2 pr-3 font-medium truncate max-w-[200px]">{d.function_name}</td>
                    <td className="py-2 pr-3">
                      <RoleBadge role={d.role} />
                    </td>
                    <td className="py-2 pr-3 text-xs text-muted-foreground">{d.model || "—"}</td>
                    <td className="py-2 pr-3">
                      <StatusBadge status={d.status} fallback={d.fallback_used} />
                    </td>
                    <td className="py-2 pr-3 text-xs text-muted-foreground">
                      {d.latency_ms ? `${d.latency_ms}ms` : "—"}
                    </td>
                    <td className="py-2 text-xs text-muted-foreground">{d.prompt_version || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Sin decisiones registradas.</p>
        )}
      </div>
    </div>
    </div>
    </div>
  );
}

function AgentCard({
  agent,
  agentKey,
  Icon,
  colorClasses,
}: {
  agent: AgentInfo;
  agentKey: string;
  Icon: React.ComponentType<{ className?: string }>;
  colorClasses: { border: string; bg: string; icon: string };
}) {
  return (
    <div className={`rounded-xl border ${colorClasses.border} ${colorClasses.bg} p-4`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`h-5 w-5 ${colorClasses.icon}`} />
          <span className="text-sm font-semibold">{agent.name}</span>
        </div>
        <Circle className={`h-2.5 w-2.5 fill-current ${STATUS_DOT[agent.status] || STATUS_DOT.idle}`} />
      </div>
      <p className="text-xs text-muted-foreground mb-2">{agent.role}</p>
      <p className="text-xs text-muted-foreground">
        {agent.model}
        {agentKey === "mote" && ` · ${agent.active_conversations ?? 0} convos`}
        {agentKey === "scout" && ` · ${agent.investigations_24h ?? 0} invest. hoy`}
        {agentKey === "executor" && ` · ${agent.invocations_24h ?? 0} calls hoy`}
        {agentKey === "reviewer" && ` · ${Math.round(((agent.approval_rate as number) ?? 0) * 100)}% aprobacion`}
      </p>
    </div>
  );
}

function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, string> = {
    executor: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300",
    reviewer: "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300",
    agent: "bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300",
    leader: "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300",
  };
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${colors[role] || "bg-gray-100 text-gray-700"}`}>
      {role}
    </span>
  );
}

function StatusBadge({ status, fallback }: { status: string; fallback: boolean }) {
  if (fallback) return <span className="text-xs text-amber-600 dark:text-amber-400">fallback</span>;
  const colors: Record<string, string> = {
    succeeded: "text-emerald-600 dark:text-emerald-400",
    degraded: "text-amber-600 dark:text-amber-400",
    failed: "text-red-600 dark:text-red-400",
  };
  return <span className={`text-xs ${colors[status] || "text-muted-foreground"}`}>{status}</span>;
}
