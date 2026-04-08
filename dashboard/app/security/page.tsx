"use client";

import { useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { SkeletonStatCard } from "@/components/shared/skeleton";
import { Button } from "@/components/ui/button";
import { NotificationListView } from "@/components/notifications/notification-list-view";
import {
  bulkUpdateNotifications,
} from "@/lib/api/client";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import type { NotificationCounts, NotificationListResponse } from "@/types";
import {
  ShieldAlert,
  ShieldCheck,
  AlertOctagon,
  AlertTriangle,
} from "lucide-react";
import { sileo } from "sileo";

export default function SecurityPage() {
  const { data: counts, isLoading: countsLoading, mutate: mutateCounts } = useApi<NotificationCounts>("/notifications/counts");
  const { data: resolvedData, mutate: mutateResolved } = useApi<NotificationListResponse>(
    "/notifications?page=1&page_size=1&category=security&status=resolved"
  );
  const [bulkLoading, setBulkLoading] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const resolvedCount = resolvedData?.total ?? 0;

  async function handleBulkResolve() {
    setBulkLoading(true);
    try {
      await sileo.promise(
        (async () => {
          const result = await bulkUpdateNotifications("mark_resolved", "security");
          await mutateCounts();
          await mutateResolved();
          setReloadKey((k) => k + 1);
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

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader
            title="Seguridad"
            description="Alertas de seguridad y eventos del sistema"
          >
            <Button
              className="rounded-xl bg-foreground text-background hover:bg-foreground/80"
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

          <NotificationListView
            fixedCategory="security"
            badgeMode="severity"
            resolvedIcon={ShieldCheck}
            emptyIcon={ShieldCheck}
            emptyTitle="Sin alertas de seguridad"
            emptyDescription="No hay alertas de seguridad que coincidan con los filtros seleccionados. Todo esta limpio."
            countLabel={(total) => `${total} alerta${total !== 1 ? "s" : ""} de seguridad`}
            onMarkResolved={() => void mutateResolved()}
            reloadKey={reloadKey}
          />
        </div>
      </div>
    </div>
  );
}
