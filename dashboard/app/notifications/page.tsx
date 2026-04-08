"use client";

import { useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { SkeletonStatCard } from "@/components/shared/skeleton";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  NotificationListView,
  type CategoryFilter,
} from "@/components/notifications/notification-list-view";
import {
  bulkUpdateNotifications,
} from "@/lib/api/client";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import type { NotificationCounts } from "@/types";
import {
  Bell,
  BellOff,
  Briefcase,
  Check,
  CheckCheck,
  Monitor,
  ShieldAlert,
} from "lucide-react";
import { sileo } from "sileo";

const CATEGORY_TABS: { value: CategoryFilter; label: string }[] = [
  { value: "", label: "Todas" },
  { value: "business", label: "Negocio" },
  { value: "system", label: "Sistema" },
  { value: "security", label: "Seguridad" },
];

export default function NotificationsPage() {
  const { data: counts, isLoading: countsLoading, mutate: mutateCounts } = useApi<NotificationCounts>("/notifications/counts");
  const [category, setCategory] = useState<CategoryFilter>("");
  const [bulkLoading, setBulkLoading] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  async function handleBulkMarkRead() {
    setBulkLoading(true);
    try {
      await sileo.promise(
        (async () => {
          const result = await bulkUpdateNotifications(
            "mark_read",
            category || undefined
          );
          await mutateCounts();
          setReloadKey((k) => k + 1);
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

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader
            title="Notificaciones"
            description="Centro de notificaciones y alertas del sistema"
          >
            <Button
              className="rounded-xl bg-foreground text-background hover:bg-foreground/80"
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
                  colorScheme="muted"
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

          {/* Category tabs */}
          <div className="flex items-center gap-1 rounded-xl bg-muted p-1">
            {CATEGORY_TABS.map((tab) => (
              <button
                key={tab.value}
                onClick={() => setCategory(tab.value)}
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

          <NotificationListView
            fixedCategory={category}
            badgeMode="category"
            resolvedIcon={Check}
            emptyIcon={BellOff}
            emptyTitle="Sin notificaciones"
            emptyDescription="No hay notificaciones que coincidan con los filtros seleccionados."
            countLabel={(total) => `${total} notificacion${total !== 1 ? "es" : ""} en total`}
            onMarkRead={() => void mutateCounts()}
            reloadKey={reloadKey}
          />
        </div>
      </div>
    </div>
  );
}
