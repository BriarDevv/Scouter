"use client";

import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  icon?: LucideIcon;
  iconColor?: string;
  iconBg?: string;
  subtitle?: string;
}

export function StatCard({
  label,
  value,
  change,
  changeType = "neutral",
  icon: Icon,
  iconColor = "text-violet-600",
  iconBg = "bg-violet-50",
  subtitle,
}: StatCardProps) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-500">{label}</p>
          <p className="font-data text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
          {(change || subtitle) && (
            <div className="flex items-center gap-1.5">
              {change && (
                <span
                  className={cn(
                    "text-xs font-medium",
                    changeType === "positive" && "text-emerald-600",
                    changeType === "negative" && "text-red-500",
                    changeType === "neutral" && "text-slate-500"
                  )}
                >
                  {change}
                </span>
              )}
              {subtitle && <span className="text-xs text-slate-400">{subtitle}</span>}
            </div>
          )}
        </div>
        {Icon && (
          <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl", iconBg)}>
            <Icon className={cn("h-5 w-5", iconColor)} />
          </div>
        )}
      </div>
    </div>
  );
}
