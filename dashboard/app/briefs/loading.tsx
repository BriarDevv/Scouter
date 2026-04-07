import { SkeletonCard } from "@/components/shared/skeleton";

export default function BriefsLoading() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          {/* Page header skeleton */}
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div className="h-7 w-20 animate-pulse rounded-lg bg-muted" />
              <div className="h-4 w-64 animate-pulse rounded-lg bg-muted" />
            </div>
            <div className="h-8 w-28 animate-pulse rounded-xl bg-muted" />
          </div>

          {/* Content skeleton */}
          <div className="grid gap-4 md:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} className="h-[200px]" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
