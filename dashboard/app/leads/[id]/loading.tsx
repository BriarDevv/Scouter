import { SkeletonCard } from "@/components/shared/skeleton";

export default function LeadDetailLoading() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          {/* Back link + header skeleton */}
          <div className="space-y-4">
            <div className="h-4 w-20 animate-pulse rounded-lg bg-muted" />
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <div className="h-7 w-48 animate-pulse rounded-lg bg-muted" />
                <div className="h-4 w-64 animate-pulse rounded-lg bg-muted" />
              </div>
              <div className="flex items-center gap-2">
                <div className="h-8 w-24 animate-pulse rounded-xl bg-muted" />
                <div className="h-8 w-24 animate-pulse rounded-xl bg-muted" />
              </div>
            </div>
          </div>

          {/* Detail cards */}
          <div className="grid gap-6 lg:grid-cols-2">
            <SkeletonCard className="h-[280px]" />
            <SkeletonCard className="h-[280px]" />
          </div>

          {/* Activity / replies section */}
          <SkeletonCard className="h-[300px]" />
        </div>
      </div>
    </div>
  );
}
