"use client";

import { StatCard } from "@/components/shared/stat-card";
import {
  Users, Send, MessageSquare, Trophy,
  UserCheck, CalendarCheck, TrendingUp,
} from "lucide-react";
import type { DashboardStats } from "@/types";
import { formatPercent, formatNumber } from "@/lib/formatters";

export function StatsGrid({ stats }: { stats: DashboardStats }) {
  return (
    <div className="space-y-4">
      {/* Primary: 4 clickable cards */}
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
          change={formatPercent(stats.conversion_rate) + " conv. rate"}
          changeType="positive"
          icon={Trophy}
          colorScheme="green"
          href="/leads?status=won"
        />
      </div>

      {/* Secondary: compact row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Calificados"
          value={formatNumber(stats.qualified)}
          subtitle={formatPercent(stats.qualified / stats.total_leads)}
          icon={UserCheck}
          colorScheme="violet"
        />
        <StatCard
          label="Reuniones"
          value={formatNumber(stats.meetings)}
          change={formatPercent(stats.meeting_rate)}
          changeType="positive"
          icon={CalendarCheck}
          colorScheme="teal"
        />
        <StatCard
          label="Score Promedio"
          value={stats.avg_score.toFixed(1)}
          icon={TrendingUp}
          colorScheme="indigo"
        />
        <StatCard
          label="Velocidad Pipeline"
          value={`${stats.pipeline_velocity.toFixed(1)}d`}
          subtitle="promedio hasta cierre"
          icon={TrendingUp}
          colorScheme="cyan"
        />
      </div>
    </div>
  );
}
