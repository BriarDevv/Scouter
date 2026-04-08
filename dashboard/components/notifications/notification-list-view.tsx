"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { truncate } from "@/lib/formatters";
import {
  getNotifications,
  updateNotificationStatus,
} from "@/lib/api/client";
import type { NotificationItem, NotificationListResponse } from "@/types";
import {
  Bell,
  BellOff,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  MessageCircle,
  Shield,
  ShieldCheck,
  Info,
  AlertTriangle,
  AlertOctagon,
  type LucideIcon,
} from "lucide-react";
import { sileo } from "sileo";

export type CategoryFilter = "" | "business" | "system" | "security";
export type SeverityFilter = "" | "info" | "warning" | "high" | "critical";
export type StatusFilter = "" | "unread" | "read" | "resolved";

export const SEVERITY_CHIPS: { value: SeverityFilter; label: string }[] = [
  { value: "", label: "Todas" },
  { value: "info", label: "Info" },
  { value: "warning", label: "Warning" },
  { value: "high", label: "Alta" },
  { value: "critical", label: "Critica" },
];

export const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "unread", label: "Sin leer" },
  { value: "read", label: "Leidas" },
  { value: "resolved", label: "Resueltas" },
];

export const SEVERITY_DOT_STYLES: Record<string, string> = {
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

export const PAGE_SIZE = 25;

export function SeverityDot({ severity }: { severity: string }) {
  return (
    <span
      className={cn(
        "inline-block h-2.5 w-2.5 rounded-full shrink-0",
        SEVERITY_DOT_STYLES[severity] ?? "bg-slate-400"
      )}
    />
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
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

export function CategoryBadge({ category }: { category: string }) {
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

export function WhatsAppIndicator({ channelState }: { channelState: Record<string, unknown> | null }) {
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

interface NotificationListViewProps {
  /** When provided, locks the API call to this category (security page uses "security"). */
  fixedCategory?: CategoryFilter;
  /** Render the badge as severity (security page) or category (notifications page) */
  badgeMode?: "severity" | "category";
  /** Icon to show in resolved state; defaults to Check */
  resolvedIcon?: LucideIcon;
  /** Empty state icon */
  emptyIcon?: LucideIcon;
  /** Empty state title */
  emptyTitle?: string;
  /** Empty state description */
  emptyDescription?: string;
  /** Count label in pagination footer (receives total count) */
  countLabel?: (total: number) => string;
  /** Called after mark-read so parent can update its counts */
  onMarkRead?: () => void;
  /** Called after mark-resolved so parent can update its counts */
  onMarkResolved?: () => void;
  /** Externally-triggered reload key — incrementing forces a reload */
  reloadKey?: number;
}

export function NotificationListView({
  fixedCategory,
  badgeMode = "category",
  resolvedIcon: ResolvedIcon = Check,
  emptyIcon: EmptyIcon = BellOff,
  emptyTitle = "Sin notificaciones",
  emptyDescription = "No hay notificaciones que coincidan con los filtros seleccionados.",
  countLabel = (total) => `${total} notificacion${total !== 1 ? "es" : ""} en total`,
  onMarkRead,
  onMarkResolved,
  reloadKey = 0,
}: NotificationListViewProps) {
  const [response, setResponse] = useState<NotificationListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [severity, setSeverity] = useState<SeverityFilter>("");
  const [status, setStatus] = useState<StatusFilter>("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getNotifications({
        page,
        page_size: PAGE_SIZE,
        category: fixedCategory || undefined,
        severity: severity || undefined,
        status: status || undefined,
      });
      setResponse(data);
    } catch (err) {
      console.error("notifications_fetch_failed", err);
    } finally {
      setLoading(false);
    }
  }, [page, severity, status, fixedCategory]);

  useEffect(() => {
    void loadNotifications();
  }, [loadNotifications]);

  // Reset page when category changes externally
  useEffect(() => {
    setPage(1);
  }, [fixedCategory]);

  // External reload trigger
  useEffect(() => {
    if (reloadKey > 0) void loadNotifications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey]);

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
      onMarkRead?.();
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
      onMarkResolved?.();
    } catch (err) {
      sileo.error({
        title: "Error",
        description: err instanceof Error ? err.message : "No se pudo resolver.",
      });
    } finally {
      setActionLoading(null);
    }
  }

  const items = response?.items ?? [];
  const total = response?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <>
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
                  ? "bg-muted dark:bg-muted text-foreground dark:text-foreground"
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
                  ? "bg-muted dark:bg-muted text-foreground dark:text-foreground"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
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
          icon={EmptyIcon}
          title={emptyTitle}
          description={emptyDescription}
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
                    isUnread && !isCritical && "bg-muted/30 dark:bg-muted/30"
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
                          <ResolvedIcon className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-1">
                        {truncate(item.message, 120)}
                      </p>
                    </div>

                    {/* Meta */}
                    <div className="flex shrink-0 items-center gap-2">
                      {badgeMode === "severity" ? (
                        <SeverityBadge severity={item.severity} />
                      ) : (
                        <>
                          <WhatsAppIndicator channelState={item.channel_state} />
                          <CategoryBadge category={item.category} />
                        </>
                      )}
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
            <span className="text-xs text-muted-foreground">{countLabel(total)}</span>
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
    </>
  );
}
