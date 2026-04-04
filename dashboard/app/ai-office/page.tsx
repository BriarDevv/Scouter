"use client";

import { useEffect, useState } from "react";
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
import { apiFetch } from "@/lib/api/client";

interface AgentInfo {
  name: string;
  role: string;
  model: string;
  status: string;
  [key: string]: unknown;
}

interface AiOfficeStatus {
  agents: {
    mote: AgentInfo;
    scout: AgentInfo;
    executor: AgentInfo;
    reviewer: AgentInfo;
  };
  outcomes: {
    total_won: number;
    total_lost: number;
  };
}

interface DecisionRecord {
  id: string;
  function_name: string;
  role: string;
  model: string | null;
  status: string;
  latency_ms: number | null;
  fallback_used: boolean;
  target_type: string | null;
  prompt_id: string | null;
  prompt_version: string | null;
  created_at: string | null;
}

interface InvestigationRecord {
  id: string;
  lead_id: string;
  agent_model: string;
  pages_visited: { url: string; title: string | null }[];
  findings: Record<string, unknown>;
  loops_used: number;
  duration_ms: number;
  error: string | null;
  created_at: string | null;
}

const AGENT_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  mote: Brain,
  scout: Search,
  executor: Sparkles,
  reviewer: CheckCircle,
};

const AGENT_COLORS: Record<string, string> = {
  mote: "violet",
  scout: "cyan",
  executor: "blue",
  reviewer: "emerald",
};

const STATUS_DOT: Record<string, string> = {
  online: "text-emerald-500",
  active: "text-emerald-500",
  idle: "text-gray-400",
};

export default function AiOfficePage() {
  const [status, setStatus] = useState<AiOfficeStatus | null>(null);
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);
  const [investigations, setInvestigations] = useState<InvestigationRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [statusRes, decisionsRes, investigationsRes] = await Promise.allSettled([
          apiFetch<AiOfficeStatus>("/ai-office/status"),
          apiFetch<DecisionRecord[]>("/ai-office/decisions?limit=15"),
          apiFetch<InvestigationRecord[]>("/ai-office/investigations?limit=5"),
        ]);
        if (statusRes.status === "fulfilled") setStatus(statusRes.value);
        if (decisionsRes.status === "fulfilled") setDecisions(decisionsRes.value);
        if (investigationsRes.status === "fulfilled") setInvestigations(investigationsRes.value);
      } catch {
        // API may not be running
      } finally {
        setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 10_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Office"
        description="Estado del equipo de inteligencia artificial de Scouter"
      />

      {/* Agent Status Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {status
          ? (["mote", "scout", "executor", "reviewer"] as const).map((key) => {
              const agent = status.agents[key];
              const Icon = AGENT_ICONS[key];
              const color = AGENT_COLORS[key];
              return (
                <AgentCard key={key} agent={agent} agentKey={key} Icon={Icon} color={color} />
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
        {investigations.length > 0 ? (
          <div className="space-y-2">
            {investigations.map((inv) => (
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

      {/* Decision Log */}
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Zap className="h-4 w-4 text-violet-600 dark:text-violet-400" />
          <h3 className="text-sm font-medium">Decisiones recientes</h3>
        </div>
        {decisions.length > 0 ? (
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
                {decisions.map((d) => (
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
  );
}

function AgentCard({
  agent,
  agentKey,
  Icon,
  color,
}: {
  agent: AgentInfo;
  agentKey: string;
  Icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  const borderColor = `border-${color}-100 dark:border-${color}-900/30`;
  const bgColor = `bg-${color}-50/30 dark:bg-${color}-950/20`;
  const iconColor = `text-${color}-600 dark:text-${color}-400`;

  return (
    <div className={`rounded-xl border ${borderColor} ${bgColor} p-4`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`h-5 w-5 ${iconColor}`} />
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
