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
  Bell,
  BellOff,
  Briefcase,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Info,
  Monitor,
  ShieldAlert,
  AlertTriangle,
  AlertOctagon,
  MessageCircle,
} from "lucide-react";
import { sileo } from "sileo";

type CategoryFilter = "" | "business" | "system" | "security";
type SeverityFilter = "" | "info" | "warning" | "high" | "critical";
type StatusFilter = "" | "unread" | "read" | "resolved";

const CATEGORY_TABS: { value: CategoryFilter; label: string }[] = [
  { value: "", label: "Todas" },
  { value: "business", label: "Negocio" },
  { value: "system", label: "Sistema" },
  { value: "security", label: "Seguridad" },
];

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

const SEVERITY_ICON: Record<string, React.ElementType> = {
  info: Info,
  warning: AlertTriangle,
  high: AlertOctagon,
  critical: AlertOctagon,
};

const CATEGORY_BADGE_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  business: {
    bg: "bg-blue-50 dark:bg-blue-950/40",
    color: "text-blue-700 dark:text-blue-300",
    label: "Negocio",
  },
  system: {
    bg: "bg-slate-100 dark:bg-slate-800/50",
    color: "text-slate-700 dark:text-slate-300",
    label: "Sistema",
  },
  security: {
    bg: "bg-red-50 dark:bg-red-950/40",
    color: "text-red-700 dark:text-red-300",
    label: "Seguridad",
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

function CategoryBadge({ category }: { category: string }) {
  const config = CATEGORY_BADGE_STYLES[category];
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

function WhatsAppIndicator({ channelState }: { channelState: Record<string, unknown> | null }) {
  if (!channelState?.whatsapp) return null;
  const wa = channelState.whatsapp as { status?: string };
  const status = wa.status;
  return (
    <span
      title={`WhatsApp: ${status}`}
      className={cn(
        "inline-flex items-center gap-1 text-xs",
        status === "delivered"
          ? "text-emerald-600 dark:text-emerald-400"
          : status === "failed"
            ? "text-red-500 dark:text-red-400"
            : "text-muted-foreground"
      )}
    >
      <MessageCircle className="h-3.5 w-3.5" />
    </span>
  );
}

export default function NotificationsPage() {
  const [counts, setCounts] = useState<NotificationCounts | null>(null);
  const [response, setResponse] = useState<NotificationListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [countsLoading, setCountsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState<CategoryFilter>("");
  const [severity, setSeverity] = useState<SeverityFilter>("");
  const [status, setStatus] = useState<StatusFilter>("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);

  const loadCounts = useCallback(async () => {
    setCountsLoading(true);
    try {
      const data = await getNotificationCounts();
      setCounts(data);
    } catch {
      // counts are non-critical; leave null
    } finally {
      setCountsLoading(false);
    }
  }, []);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getNotifications({
        page,
        page_size: PAGE_SIZE,
        category: category || undefined,
        severity: severity || undefined,
        status: status || undefined,
      });
      setResponse(data);
    } catch {
      // keep previous data on failure
    } finally {
      setLoading(false);
    }
  }, [page, category, severity, status]);

  useEffect(() => {
    void loadCounts();
  }, [loadCounts]);

  useEffect(() => {
    void loadNotifications();
  }, [loadNotifications]);

  function resetFiltersAndLoad(
    cat: CategoryFilter,
    sev: SeverityFilter,
    st: StatusFilter
  ) {
    setPage(1);
    setCategory(cat);
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
      setCounts((prev) =>
        prev ? { ...prev, total_unread: Math.max(0, prev.total_unread - 1) } : prev
      );
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
    } catch (err) {
      sileo.error({
        title: "Error",
        description: err instanceof Error ? err.message : "No se pudo resolver.",
      });
    } finally {
      setActionLoading(null);
    }
  }

  async function handleBulkMarkRead() {
    setBulkLoading(true);
    try {
      await sileo.promise(
        (async () => {
          const result = await bulkUpdateNotifications(
            "mark_read",
            category || undefined
          );
          await loadCounts();
          await loadNotifications();
          return result;
        })(),
        {
          loading: { title: "Marcando como leidas..." },
          success: { title: "Notificaciones marcadas como leidas" },
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
            title="Notificaciones"
            description="Centro de notificaciones y alertas del sistema"
      >
        <Button
          className="rounded-xl bg-violet-600 text-white hover:bg-violet-700"
          onClick={() => void handleBulkMarkRead()}
          disabled={bulkLoading || (counts?.total_unread === 0)}
        >
          <CheckCheck className="mr-2 h-4 w-4" />
          Marcar todo como leido
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
              label="Total sin leer"
              value={counts?.total_unread ?? 0}
              icon={Bell}
              colorScheme="violet"
            />
            <StatCard
              label="Negocio"
              value={counts?.business ?? 0}
              icon={Briefcase}
              colorScheme="blue"
            />
            <StatCard
              label="Sistema"
              value={counts?.system ?? 0}
              icon={Monitor}
              colorScheme="amber"
            />
            <StatCard
              label="Seguridad"
              value={counts?.security ?? 0}
              icon={ShieldAlert}
              colorScheme="red"
            />
          </>
        )}
      </div>

      {/* Filters */}
      <div className="space-y-3">
        {/* Category tabs */}
        <div className="flex items-center gap-1 rounded-xl bg-muted p-1">
          {CATEGORY_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => resetFiltersAndLoad(tab.value, severity, status)}
              className={cn(
                "rounded-lg px-3 py-1.5 text-sm font-medium font-heading transition-colors",
                category === tab.value
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Severity chips */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium text-muted-foreground mr-1">Severidad:</span>
            {SEVERITY_CHIPS.map((chip) => (
              <button
                key={chip.value}
                onClick={() => resetFiltersAndLoad(category, chip.value, status)}
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
                onClick={() => resetFiltersAndLoad(category, severity, opt.value)}
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
      </div>

      {/* Notification List */}
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
          icon={BellOff}
          title="Sin notificaciones"
          description="No hay notificaciones que coincidan con los filtros seleccionados."
        />
      ) : (
        <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
          <div className="divide-y divide-border/50">
            {items.map((item) => {
              const isExpanded = expandedId === item.id;
              const isUnread = item.status === "unread";
              const isResolved = item.status === "resolved";

              return (
                <div
                  key={item.id}
                  className={cn(
                    "group transition-colors",
                    isUnread && "bg-violet-50/30 dark:bg-violet-950/10"
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
                          <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-1">
                        {truncate(item.message, 120)}
                      </p>
                    </div>

                    {/* Meta */}
                    <div className="flex shrink-0 items-center gap-2">
                      <WhatsAppIndicator channelState={item.channel_state} />
                      <CategoryBadge category={item.category} />
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
                            <CheckCheck className="mr-1 h-3.5 w-3.5" />
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
              {total} notificacion{total !== 1 ? "es" : ""} en total
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
