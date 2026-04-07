import { SkeletonCard } from "@/components/shared/skeleton";

export default function OnboardingLoading() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          {/* Page header skeleton */}
          <div className="space-y-2">
            <div className="h-7 w-36 animate-pulse rounded-lg bg-muted" />
            <div className="h-4 w-72 animate-pulse rounded-lg bg-muted" />
          </div>

          {/* Steps skeleton */}
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <SkeletonCard key={i} className="h-24" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
