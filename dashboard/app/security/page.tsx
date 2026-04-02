"use client";

import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { SkeletonStatCard } from "@/components/shared/skeleton";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { truncate } from "@/lib/formatters";
import {
  getNotifications,
  getNotificationCounts,
  updateNotificationStatus,
  bulkUpdateNotifications,
} from "@/lib/api/client";
import type { NotificationItem, NotificationCounts, NotificationListResponse } from "@/types";
import {
  Check,
  CheckCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertOctagon,
  AlertTriangle,
  Info,
} from "lucide-react";
import { sileo } from "sileo";

type SeverityFilter = "" | "info" | "warning" | "high" | "critical";
type StatusFilter = "" | "unread" | "read" | "resolved";

const SEVERITY_CHIPS: { value: SeverityFilter; label: string }[] = [
  { value: "", label: "Todas" },
  { value: "info", label: "Info" },
  { value: "warning", label: "Warning" },
  { value: "high", label: "Alta" },
  { value: "critical", label: "Critica" },
];

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "unread", label: "Sin leer" },
  { value: "read", label: "Leidas" },
  { value: "resolved", label: "Resueltas" },
];

const SEVERITY_DOT_STYLES: Record<string, string> = {
  info: "bg-blue-500",
  warning: "bg-amber-500",
  high: "bg-red-500",
  critical: "bg-red-600 animate-pulse",
};

const SEVERITY_BADGE_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  info: {
    bg: "bg-blue-50 dark:bg-blue-950/40",
    color: "text-blue-700 dark:text-blue-300",
    label: "Info",
  },
  warning: {
    bg: "bg-amber-50 dark:bg-amber-950/40",
    color: "text-amber-700 dark:text-amber-300",
    label: "Warning",
  },
  high: {
    bg: "bg-red-50 dark:bg-red-950/40",
    color: "text-red-700 dark:text-red-300",
    label: "Alta",
  },
  critical: {
    bg: "bg-red-100 dark:bg-red-950/60",
    color: "text-red-800 dark:text-red-200",
    label: "Critica",
  },
};

const PAGE_SIZE = 25;

function SeverityDot({ severity }: { severity: string }) {
  return (
    <span
      className={cn(
        "inline-block h-2.5 w-2.5 rounded-full shrink-0",
        SEVERITY_DOT_STYLES[severity] ?? "bg-slate-400"
      )}
    />
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const config = SEVERITY_BADGE_STYLES[severity];
  if (!config) return null;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        config.bg,
        config.color
      )}
    >
      {config.label}
    </span>
  );
}

export default function SecurityPage() {
  const [counts, setCounts] = useState<NotificationCounts | null>(null);
  const [response, setResponse] = useState<NotificationListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [countsLoading, setCountsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [severity, setSeverity] = useState<SeverityFilter>("");
  const [status, setStatus] = useState<StatusFilter>("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);

  // Track resolved count from initial load for the stat card
  const [resolvedCount, setResolvedCount] = useState(0);

  const loadCounts = useCallback(async () => {
    setCountsLoading(true);
    try {
      const data = await getNotificationCounts();
      setCounts(data);
    } catch {
      // non-critical
    } finally {
      setCountsLoading(false);
    }
  }, []);

  const loadResolvedCount = useCallback(async () => {
    try {
      const data = await getNotifications({
        page: 1,
        page_size: 1,
        category: "security",
        status: "resolved",
      });
      setResolvedCount(data.total);
    } catch {
      // non-critical
    }
  }, []);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getNotifications({
        page,
        page_size: PAGE_SIZE,
        category: "security",
        severity: severity || undefined,
        status: status || undefined,
      });
      setResponse(data);
    } catch {
      // keep previous data
    } finally {
      setLoading(false);
    }
  }, [page, severity, status]);

  useEffect(() => {
    void loadCounts();
    void loadResolvedCount();
  }, [loadCounts, loadResolvedCount]);

  useEffect(() => {
    void loadNotifications();
  }, [loadNotifications]);

  function resetFiltersAndLoad(sev: SeverityFilter, st: StatusFilter) {
    setPage(1);
    setSeverity(sev);
    setStatus(st);
  }

  async function handleMarkRead(item: NotificationItem) {
    setActionLoading(item.id);
    try {
      await updateNotificationStatus(item.id, "read");
      setResponse((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map((n) =>
            n.id === item.id ? { ...n, status: "read", read_at: new Date().toISOString() } : n
          ),
          unread_count: Math.max(0, prev.unread_count - 1),
        };
      });
    } catch (err) {
      sileo.error({
        title: "Error",
        description: err instanceof Error ? err.message : "No se pudo actualizar.",
      });
    } finally {
      setActionLoading(null);
    }
  }

  async function handleMarkResolved(item: NotificationItem) {
    setActionLoading(item.id);
    try {
      await updateNotificationStatus(item.id, "resolved");
      setResponse((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map((n) =>
            n.id === item.id
              ? { ...n, status: "resolved", resolved_at: new Date().toISOString() }
              : n
          ),
        };
      });
      setResolvedCount((c) => c + 1);
    } catch (err) {
      sileo.error({
        title: "Error",
        description: err instanceof Error ? err.message : "No se pudo resolver.",
      });
    } finally {
      setActionLoading(null);
    }
  }

  async function handleBulkResolve() {
    setBulkLoading(true);
    try {
      await sileo.promise(
        (async () => {
          const result = await bulkUpdateNotifications("mark_resolved", "security");
          await loadCounts();
          await loadResolvedCount();
          await loadNotifications();
          return result;
        })(),
        {
          loading: { title: "Resolviendo alertas de seguridad..." },
          success: { title: "Alertas de seguridad resueltas" },
          error: (err: unknown) => ({
            title: "Error",
            description: err instanceof Error ? err.message : "No se pudo completar.",
          }),
        }
      );
    } finally {
      setBulkLoading(false);
    }
  }

  const items = response?.items ?? [];
  const total = response?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader
            title="Seguridad"
            description="Alertas de seguridad y eventos del sistema"
      >
        <Button
          className="rounded-xl bg-violet-600 text-white hover:bg-violet-700"
          onClick={() => void handleBulkResolve()}
          disabled={bulkLoading || (counts?.security === 0)}
        >
          <ShieldCheck className="mr-2 h-4 w-4" />
          Resolver todas
        </Button>
      </PageHeader>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {countsLoading ? (
          <>
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
          </>
        ) : (
          <>
            <StatCard
              label="Total alertas"
              value={counts?.security ?? 0}
              icon={ShieldAlert}
              colorScheme="red"
            />
            <StatCard
              label="Criticas"
              value={counts?.critical ?? 0}
              icon={AlertOctagon}
              colorScheme="red"
            />
            <StatCard
              label="Altas"
              value={counts?.high ?? 0}
              icon={AlertTriangle}
              colorScheme="amber"
            />
            <StatCard
              label="Resueltas"
              value={resolvedCount}
              icon={ShieldCheck}
              colorScheme="emerald"
            />
          </>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Severity chips */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground mr-1">Severidad:</span>
          {SEVERITY_CHIPS.map((chip) => (
            <button
              key={chip.value}
              onClick={() => resetFiltersAndLoad(chip.value, status)}
              className={cn(
                "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                severity === chip.value
                  ? "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              {chip.label}
            </button>
          ))}
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground mr-1">Estado:</span>
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => resetFiltersAndLoad(severity, opt.value)}
              className={cn(
                "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                status === opt.value
                  ? "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Security Notification List */}
      {loading ? (
        <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
          <div className="divide-y divide-border/50">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-start gap-4 px-5 py-4 animate-pulse">
                <div className="mt-1 h-2.5 w-2.5 rounded-full bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-48 rounded bg-muted" />
                  <div className="h-3 w-72 rounded bg-muted" />
                </div>
                <div className="h-5 w-16 rounded-full bg-muted" />
                <div className="h-3 w-12 rounded bg-muted" />
              </div>
            ))}
          </div>
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Shield}
          title="Sin alertas de seguridad"
          description="No hay alertas de seguridad que coincidan con los filtros seleccionados. Todo esta limpio."
        />
      ) : (
        <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
          <div className="divide-y divide-border/50">
            {items.map((item) => {
              const isExpanded = expandedId === item.id;
              const isUnread = item.status === "unread";
              const isResolved = item.status === "resolved";
              const isCritical = item.severity === "critical";

              return (
                <div
                  key={item.id}
                  className={cn(
                    "group transition-colors",
                    isUnread && isCritical && "bg-red-50/40 dark:bg-red-950/10",
                    isUnread && !isCritical && "bg-violet-50/30 dark:bg-violet-950/10"
                  )}
                >
                  {/* Main row */}
                  <button
                    type="button"
                    className="flex w-full items-start gap-4 px-5 py-4 text-left hover:bg-muted/50 transition-colors"
                    onClick={() => setExpandedId(isExpanded ? null : item.id)}
                  >
                    {/* Severity dot */}
                    <div className="mt-1.5 shrink-0">
                      <SeverityDot severity={item.severity} />
                    </div>

                    {/* Content */}
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            "text-sm font-heading",
                            isUnread ? "font-semibold text-foreground" : "font-medium text-foreground/80"
                          )}
                        >
                          {item.title}
                        </span>
                        {isResolved && (
                          <ShieldCheck className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-1">
                        {truncate(item.message, 120)}
                      </p>
                    </div>

                    {/* Meta */}
                    <div className="flex shrink-0 items-center gap-2">
                      <SeverityBadge severity={item.severity} />
                      <RelativeTime
                        date={item.created_at}
                        className="text-xs text-muted-foreground whitespace-nowrap"
                      />
                      <ChevronDown
                        className={cn(
                          "h-4 w-4 text-muted-foreground transition-transform",
                          isExpanded && "rotate-180"
                        )}
                      />
                    </div>
                  </button>

                  {/* Expanded detail */}
                  {isExpanded && (
                    <div className="border-t border-border/30 bg-muted/30 px-5 py-4 pl-12">
                      <p className="text-sm text-foreground/90 whitespace-pre-wrap mb-3">
                        {item.message}
                      </p>

                      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground mb-3">
                        <span>
                          Tipo: <span className="font-medium text-foreground/70">{item.type}</span>
                        </span>
                        {item.source_kind && (
                          <span>
                            Origen: <span className="font-medium text-foreground/70">{item.source_kind}</span>
                          </span>
                        )}
                        <span>
                          Estado:{" "}
                          <span className="font-medium text-foreground/70">
                            {item.status === "unread"
                              ? "Sin leer"
                              : item.status === "read"
                                ? "Leida"
                                : item.status === "acknowledged"
                                  ? "Reconocida"
                                  : "Resuelta"}
                          </span>
                        </span>
                        {item.metadata && Object.keys(item.metadata).length > 0 && (
                          <span>
                            Metadata:{" "}
                            <span className="font-data font-medium text-foreground/70">
                              {JSON.stringify(item.metadata)}
                            </span>
                          </span>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        {isUnread && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="rounded-lg text-xs"
                            disabled={actionLoading === item.id}
                            onClick={() => void handleMarkRead(item)}
                          >
                            <Check className="mr-1 h-3.5 w-3.5" />
                            Marcar como leida
                          </Button>
                        )}
                        {!isResolved && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="rounded-lg text-xs"
                            disabled={actionLoading === item.id}
                            onClick={() => void handleMarkResolved(item)}
                          >
                            <ShieldCheck className="mr-1 h-3.5 w-3.5" />
                            Resolver
                          </Button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Pagination footer */}
          <div className="flex items-center justify-between border-t border-border px-5 py-3">
            <span className="text-xs text-muted-foreground">
              {total} alerta{total !== 1 ? "s" : ""} de seguridad
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon-sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-xs text-muted-foreground font-data px-2">
                {page} / {totalPages || 1}
              </span>
              <Button
                variant="ghost"
                size="icon-sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}
        </div>
      </div>
    </div>
  );
}
