"use client";

import { useState } from "react";
import { StatCard } from "@/components/shared/stat-card";
import {
  Users, Send, MessageSquare, Trophy,
  UserCheck, CalendarCheck, TrendingUp, ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { DashboardStats } from "@/types";
import { formatPercent, formatNumber } from "@/lib/formatters";

export function StatsGrid({ stats }: { stats: DashboardStats }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="space-y-3">
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

      {/* Secondary: expandable row */}
      {expanded && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard
            label="Calificados"
            value={formatNumber(stats.qualified)}
            subtitle={formatPercent(stats.total_leads > 0 ? stats.qualified / stats.total_leads : 0)}
            icon={UserCheck}
            colorScheme="muted"
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
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 mx-auto text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")} />
        {expanded ? "Menos métricas" : "Más métricas"}
      </button>
    </div>
  );
}
