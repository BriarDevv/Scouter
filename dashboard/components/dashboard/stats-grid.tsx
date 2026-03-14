"use client";

import { StatCard } from "@/components/shared/stat-card";
import {
  Users, UserPlus, UserCheck, Send, MessageSquare, CalendarCheck, Trophy, TrendingUp,
} from "lucide-react";
import type { DashboardStats } from "@/types";
import { formatPercent, formatNumber } from "@/lib/formatters";

export function StatsGrid({ stats }: { stats: DashboardStats }) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <StatCard
        label="Total Leads"
        value={formatNumber(stats.total_leads)}
        change={`+${stats.new_today} hoy`}
        changeType="positive"
        icon={Users}
        iconBg="bg-muted"
        iconColor="text-muted-foreground"
      />
      <StatCard
        label="Calificados"
        value={formatNumber(stats.qualified)}
        subtitle={formatPercent(stats.qualified / stats.total_leads)}
        icon={UserCheck}
        iconBg="bg-violet-50"
        iconColor="text-violet-600"
      />
      <StatCard
        label="Contactados"
        value={formatNumber(stats.contacted)}
        change={formatPercent(stats.open_rate) + " open rate"}
        changeType="neutral"
        icon={Send}
        iconBg="bg-amber-50"
        iconColor="text-amber-600"
      />
      <StatCard
        label="Respondieron"
        value={formatNumber(stats.replied)}
        change={formatPercent(stats.reply_rate) + " reply rate"}
        changeType="positive"
        icon={MessageSquare}
        iconBg="bg-emerald-50"
        iconColor="text-emerald-600"
      />
      <StatCard
        label="Reuniones"
        value={formatNumber(stats.meetings)}
        change={formatPercent(stats.meeting_rate)}
        changeType="positive"
        icon={CalendarCheck}
        iconBg="bg-teal-50"
        iconColor="text-teal-600"
      />
      <StatCard
        label="Ganados"
        value={formatNumber(stats.won)}
        change={formatPercent(stats.conversion_rate) + " conv. rate"}
        changeType="positive"
        icon={Trophy}
        iconBg="bg-green-50"
        iconColor="text-green-600"
      />
      <StatCard
        label="Score Promedio"
        value={stats.avg_score.toFixed(1)}
        icon={TrendingUp}
        iconBg="bg-indigo-50"
        iconColor="text-indigo-600"
      />
      <StatCard
        label="Velocidad Pipeline"
        value={`${stats.pipeline_velocity.toFixed(1)}d`}
        subtitle="promedio hasta cierre"
        icon={TrendingUp}
        iconBg="bg-cyan-50"
        iconColor="text-cyan-600"
      />
    </div>
  );
}
