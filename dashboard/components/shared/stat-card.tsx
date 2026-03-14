"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { ChevronRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";

const COLOR_SCHEMES: Record<string, { iconBg: string; iconColor: string }> = {
  violet:  { iconBg: "bg-violet-50 dark:bg-violet-950/30",  iconColor: "text-violet-600 dark:text-violet-400" },
  emerald: { iconBg: "bg-emerald-50 dark:bg-emerald-950/30", iconColor: "text-emerald-600 dark:text-emerald-400" },
  amber:   { iconBg: "bg-amber-50 dark:bg-amber-950/30",   iconColor: "text-amber-600 dark:text-amber-400" },
  cyan:    { iconBg: "bg-cyan-50 dark:bg-cyan-950/30",    iconColor: "text-cyan-600 dark:text-cyan-400" },
  teal:    { iconBg: "bg-teal-50 dark:bg-teal-950/30",    iconColor: "text-teal-600 dark:text-teal-400" },
  green:   { iconBg: "bg-green-50 dark:bg-green-950/30",   iconColor: "text-green-600 dark:text-green-400" },
  blue:    { iconBg: "bg-blue-50 dark:bg-blue-950/30",    iconColor: "text-blue-600 dark:text-blue-400" },
  indigo:  { iconBg: "bg-indigo-50 dark:bg-indigo-950/30",  iconColor: "text-indigo-600 dark:text-indigo-400" },
  orange:  { iconBg: "bg-orange-50 dark:bg-orange-950/30",  iconColor: "text-orange-600 dark:text-orange-400" },
  purple:  { iconBg: "bg-purple-50 dark:bg-purple-950/30",  iconColor: "text-purple-600 dark:text-purple-400" },
  fuchsia: { iconBg: "bg-fuchsia-50 dark:bg-fuchsia-950/30", iconColor: "text-fuchsia-600 dark:text-fuchsia-400" },
  red:     { iconBg: "bg-red-50 dark:bg-red-950/30",     iconColor: "text-red-600 dark:text-red-400" },
  muted:   { iconBg: "bg-muted",                          iconColor: "text-muted-foreground" },
};

interface StatCardProps {
  label: string;
  value: string | number;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  icon?: LucideIcon;
  iconColor?: string;
  iconBg?: string;
  colorScheme?: string;
  subtitle?: string;
  href?: string;
}

export function StatCard({
  label,
  value,
  change,
  changeType = "neutral",
  icon: Icon,
  iconColor,
  iconBg,
  colorScheme,
  subtitle,
  href,
}: StatCardProps) {
  const scheme = colorScheme ? COLOR_SCHEMES[colorScheme] : undefined;
  const resolvedIconBg = scheme?.iconBg ?? iconBg ?? "bg-violet-50";
  const resolvedIconColor = scheme?.iconColor ?? iconColor ?? "text-violet-600";

  const content = (
    <div className={cn(
      "rounded-2xl border border-border bg-card p-5 shadow-sm transition-shadow hover:shadow-md",
      href && "cursor-pointer"
    )}>
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <p className="font-data text-2xl font-semibold tracking-tight text-foreground">{value}</p>
          {(change || subtitle) && (
            <div className="flex items-center gap-1.5">
              {change && (
                <span
                  className={cn(
                    "text-xs font-medium",
                    changeType === "positive" && "text-emerald-600",
                    changeType === "negative" && "text-red-500",
                    changeType === "neutral" && "text-muted-foreground"
                  )}
                >
                  {change}
                </span>
              )}
              {subtitle && <span className="text-xs text-muted-foreground">{subtitle}</span>}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {Icon && (
            <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl", resolvedIconBg)}>
              <Icon className={cn("h-5 w-5", resolvedIconColor)} />
            </div>
          )}
          {href && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
        </div>
      </div>
    </div>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }

  return content;
}
