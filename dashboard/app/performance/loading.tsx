import { SkeletonStatCard, SkeletonCard } from "@/components/shared/skeleton";

export default function PerformanceLoading() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-8">
          {/* Page header skeleton */}
          <div className="space-y-2">
            <div className="h-7 w-36 animate-pulse rounded-lg bg-muted" />
            <div className="h-4 w-80 animate-pulse rounded-lg bg-muted" />
          </div>

          {/* Tab bar skeleton */}
          <div className="flex items-center gap-0 border-b border-border pb-0">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-9 w-24 animate-pulse rounded-t-lg bg-muted mx-1" />
            ))}
          </div>

          {/* Stat cards — 5-col grid */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
            {Array.from({ length: 5 }).map((_, i) => (
              <SkeletonStatCard key={i} />
            ))}
          </div>

          {/* Velocity stat cards — 4-col grid */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonStatCard key={i} />
            ))}
          </div>

          {/* Chart cards */}
          <div className="grid gap-6 lg:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} className="h-[280px]" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
