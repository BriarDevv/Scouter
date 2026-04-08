"use client";

import { StatCard } from "@/components/shared/stat-card";
import {
  Users, Send, MessageSquare, Trophy,
  TrendingUp, Eye, BarChart3, Timer,
} from "lucide-react";
import type { DashboardStats } from "@/types";
import { formatPercent, formatNumber } from "@/lib/formatters";

export function StatsGrid({ stats }: { stats: DashboardStats }) {
  return (
    <div className="space-y-4">
      {/* Primary metrics */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Total Leads"
          value={formatNumber(stats.total_leads)}
          change={`+${stats.new_today} hoy`}
          changeType="positive"
          icon={Users}
          colorScheme="muted"
          href="/leads"
        />
        <StatCard
          label="Contactados"
          value={formatNumber(stats.contacted)}
          change={formatPercent(stats.open_rate) + " open rate"}
          changeType="neutral"
          icon={Send}
          colorScheme="amber"
          href="/leads?status=contacted"
        />
        <StatCard
          label="Respondieron"
          value={formatNumber(stats.replied)}
          change={formatPercent(stats.reply_rate) + " reply rate"}
          changeType="positive"
          icon={MessageSquare}
          colorScheme="emerald"
          href="/responses"
        />
        <StatCard
          label="Ganados"
          value={formatNumber(stats.won)}
          change={formatPercent(stats.conversion_rate) + " conversion"}
          changeType="positive"
          icon={Trophy}
          colorScheme="green"
          href="/leads?status=won"
        />
      </div>

      {/* Secondary metrics */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Score Promedio"
          value={stats.avg_score.toFixed(1)}
          icon={TrendingUp}
          colorScheme="muted"
        />
        <StatCard
          label="Open Rate"
          value={formatPercent(stats.open_rate)}
          icon={Eye}
          colorScheme="muted"
        />
        <StatCard
          label="Reply Rate"
          value={formatPercent(stats.reply_rate)}
          icon={BarChart3}
          colorScheme="muted"
        />
        <StatCard
          label="Dias hasta cierre"
          value={stats.pipeline_velocity > 0 ? `${stats.pipeline_velocity.toFixed(0)}d` : "—"}
          icon={Timer}
          colorScheme="muted"
        />
      </div>
    </div>
  );
}
