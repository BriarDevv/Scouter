import { SkeletonCard } from "@/components/shared/skeleton";

export default function SettingsLoading() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          {/* Page header skeleton */}
          <div className="space-y-2">
            <div className="h-7 w-24 animate-pulse rounded-lg bg-muted" />
            <div className="h-4 w-64 animate-pulse rounded-lg bg-muted" />
          </div>

          {/* Settings sections skeleton */}
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <SkeletonCard key={i} className="h-[100px]" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
