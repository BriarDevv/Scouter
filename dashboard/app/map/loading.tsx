import { SkeletonCard } from "@/components/shared/skeleton";

export default function MapLoading() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          {/* Page header skeleton */}
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div className="h-7 w-16 animate-pulse rounded-lg bg-muted" />
              <div className="h-4 w-56 animate-pulse rounded-lg bg-muted" />
            </div>
          </div>

          {/* Map area skeleton */}
          <SkeletonCard className="h-[500px]" />
        </div>
      </div>
    </div>
  );
}
