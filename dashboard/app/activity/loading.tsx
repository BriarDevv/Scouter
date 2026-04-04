import { Skeleton, SkeletonCard } from "@/components/shared/skeleton";

export default function ActivityLoading() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-8">
          {/* Page header skeleton */}
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div className="h-7 w-32 animate-pulse rounded-lg bg-muted" />
              <div className="h-4 w-72 animate-pulse rounded-lg bg-muted" />
            </div>
            <div className="h-8 w-28 animate-pulse rounded-xl bg-muted" />
          </div>

          {/* Summary stat cards — 3-col grid */}
          <div className="grid gap-4 md:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-2xl" />
            ))}
          </div>

          {/* Active tasks placeholder */}
          <SkeletonCard className="h-[400px]" />
        </div>
      </div>
    </div>
  );
}
