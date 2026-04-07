import { SkeletonCard, SkeletonTable } from "@/components/shared/skeleton";

export default function OutreachLoading() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          {/* Page header skeleton */}
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div className="h-7 w-24 animate-pulse rounded-lg bg-muted" />
              <div className="h-4 w-64 animate-pulse rounded-lg bg-muted" />
            </div>
            <div className="flex items-center gap-2">
              <div className="h-8 w-24 animate-pulse rounded-xl bg-muted" />
              <div className="h-8 w-28 animate-pulse rounded-xl bg-muted" />
            </div>
          </div>

          {/* Table skeleton */}
          <SkeletonTable rows={8} />
        </div>
      </div>
    </div>
  );
}
