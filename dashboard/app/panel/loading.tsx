import { SkeletonStatCard, SkeletonCard } from "@/components/shared/skeleton";

export default function PanelLoading() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          {/* Page header skeleton */}
          <div className="space-y-2">
            <div className="h-7 w-36 animate-pulse rounded-lg bg-muted" />
            <div className="h-4 w-72 animate-pulse rounded-lg bg-muted" />
          </div>

          {/* Control center skeleton */}
          <div className="h-20 w-full animate-pulse rounded-2xl bg-muted" />

          {/* Key metrics — 4-col grid */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonStatCard key={i} />
            ))}
          </div>

          {/* Charts — 2-col grid */}
          <div className="grid gap-6 lg:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} className="h-[280px]" />
            ))}
          </div>

          {/* AI health + corrections — 2-col grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <SkeletonCard className="h-[200px]" />
            <SkeletonCard className="h-[200px]" />
          </div>

          {/* Territory summary skeleton */}
          <SkeletonCard className="h-[160px]" />
        </div>
      </div>
    </div>
  );
}
