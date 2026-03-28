"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { ActivityPulse } from "@/components/layout/activity-pulse";
import { API_BASE_URL } from "@/lib/constants";
import { useChatPanel } from "@/lib/hooks/use-chat-panel";
import {
  Bell,
  Inbox,
  LayoutDashboard,
  Users,
  Mail,
  BarChart3,
  PanelLeftClose,
  PanelLeftOpen,
  ShieldAlert,
  ShieldOff,
  Sparkles,
  Radar,
  MapPin,
  Settings,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/",            label: "Panel general", icon: LayoutDashboard },
  { href: "/leads",       label: "Leads",         icon: Users },
  { href: "/outreach",    label: "Outreach",      icon: Mail },
  { href: "/responses",   label: "Respuestas",    icon: Inbox },
  { href: "/performance", label: "Rendimiento",   icon: BarChart3 },
  { href: "/map",         label: "Mapa",          icon: MapPin },
  { href: "/suppression", label: "Supresión",     icon: ShieldOff },
];

const EXTRA_NAV_ITEMS = [
  { href: "/notifications", label: "Notificaciones", icon: Bell,        badge: true },
  { href: "/security",      label: "Seguridad",      icon: ShieldAlert, badge: false },
];

/** Fade text: out fast (0ms delay), in after width expands (150ms delay). */
function labelCn(collapsed: boolean) {
  return cn(
    "whitespace-nowrap transition-[opacity] overflow-hidden",
    collapsed
      ? "opacity-0 w-0 duration-100 delay-0"
      : "opacity-100 w-auto duration-200 delay-150"
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const [unreadCount, setUnreadCount] = useState(0);
  const { isOpen: chatOpen, toggle: toggleChat, sidebarCollapsed: collapsed, toggleSidebar } = useChatPanel();

  useEffect(() => {
    let active = true;
    async function fetchNotificationCounts() {
      try {
        const res = await fetch(`${API_BASE_URL}/notifications/counts`);
        if (res.ok) {
          const data = await res.json();
          if (active) {
            setUnreadCount(data.unread ?? 0);
          }
        }
      } catch {
        // Non-critical — silently ignore fetch errors
      }
    }
    fetchNotificationCounts();
    return () => { active = false; };
  }, []);

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-40 flex flex-col overflow-hidden bg-sidebar transition-all duration-300 ease-in-out",
        collapsed ? "w-[68px]" : "w-64"
      )}
    >
      {/* Header */}
      <div className="flex h-16 items-center border-b border-sidebar-border px-3">
        <button
          onClick={toggleSidebar}
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600",
            collapsed ? "mx-auto" : "ml-3"
          )}
          title={collapsed ? "Expandir sidebar" : "Minimizar sidebar"}
        >
          {collapsed
            ? <PanelLeftOpen className="h-4 w-4 text-white" />
            : <Radar className="h-4.5 w-4.5 text-white" />
          }
        </button>
        <div className={cn(labelCn(collapsed), "ml-3 flex items-center gap-1.5")}>
          <span className="font-heading text-lg font-bold tracking-tight text-sidebar-foreground">ClawScout</span>
          <span className="rounded-md bg-violet-50 dark:bg-violet-950/40 px-1.5 py-0.5 text-[10px] font-medium text-violet-600 dark:text-violet-400">v2</span>
        </div>
        {!collapsed && (
          <button
            onClick={toggleSidebar}
            className="ml-auto rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            title="Minimizar sidebar"
          >
            <PanelLeftClose className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center gap-3 rounded-xl py-2.5 text-sm font-medium font-heading transition-all duration-150",
                collapsed ? "justify-center px-0" : "px-3",
                isActive
                  ? "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className={cn("h-[18px] w-[18px] shrink-0", isActive ? "text-violet-600 dark:text-violet-400" : "")} />
              <span className={labelCn(collapsed)}>{item.label}</span>
            </Link>
          );
        })}

        {/* Notifications & Security */}
        {EXTRA_NAV_ITEMS.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={cn(
                "relative flex items-center gap-3 rounded-xl py-2.5 text-sm font-medium font-heading transition-all duration-150",
                collapsed ? "justify-center px-0" : "px-3",
                isActive
                  ? "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className={cn("h-[18px] w-[18px] shrink-0", isActive ? "text-violet-600 dark:text-violet-400" : "")} />
              <span className={cn(labelCn(collapsed), "flex-1")}>{item.label}</span>
              {item.badge && unreadCount > 0 && (
                <span className={cn(
                  "bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1",
                  collapsed && "absolute -top-1 -right-1 min-w-[16px] h-[16px] text-[9px]"
                )}>
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* AI Activity */}
      <div className={cn(
        "border-t border-sidebar-border overflow-hidden transition-all duration-200",
        collapsed ? "max-h-0 border-t-0" : "max-h-40"
      )}>
        <ActivityPulse />
      </div>

      {/* Footer */}
      <div className="border-t border-sidebar-border space-y-1 p-2">
        <div className={cn(
          "overflow-hidden transition-all duration-200",
          collapsed ? "max-h-0" : "max-h-12"
        )}>
          <ThemeToggle />
        </div>
        <button
          onClick={toggleChat}
          title={collapsed ? "Chat IA" : undefined}
          className={cn(
            "flex w-full items-center gap-3 rounded-xl py-2.5 text-sm font-medium font-heading transition-all duration-150",
            collapsed ? "justify-center px-0" : "px-3",
            chatOpen
              ? "bg-violet-600 text-white"
              : "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300 hover:bg-violet-100 dark:hover:bg-violet-950/60"
          )}
        >
          <Sparkles className="h-[18px] w-[18px] shrink-0" />
          <span className={labelCn(collapsed)}>Chat IA</span>
        </button>
        <Link
          href="/settings"
          title={collapsed ? "Configuración" : undefined}
          className={cn(
            "flex items-center gap-3 rounded-xl py-2.5 text-sm font-medium text-muted-foreground transition-all hover:bg-muted hover:text-foreground",
            collapsed ? "justify-center px-0" : "px-3"
          )}
        >
          <Settings className="h-[18px] w-[18px] shrink-0" />
          <span className={labelCn(collapsed)}>Configuración</span>
        </Link>
      </div>
    </aside>
  );
}
