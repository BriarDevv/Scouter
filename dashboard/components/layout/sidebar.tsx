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
        "fixed inset-y-0 left-0 z-40 flex flex-col overflow-hidden rounded-r-3xl bg-sidebar shadow-[2px_0_12px_-2px_rgba(0,0,0,0.1)] dark:shadow-[2px_0_12px_-2px_rgba(0,0,0,0.4)] transition-all duration-300 ease-in-out",
        collapsed ? "w-[68px]" : "w-64"
      )}
    >
      {/* Header */}
      <div className="flex h-16 items-center border-b border-sidebar-border px-3">
        {collapsed ? (
          <button
            onClick={toggleSidebar}
            className="mx-auto flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600"
            title="Expandir sidebar"
          >
            <PanelLeftOpen className="h-4 w-4 text-white" />
          </button>
        ) : (
          <>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600 ml-3">
              <Radar className="h-4.5 w-4.5 text-white" />
            </div>
            <div className="ml-3">
              <span className="font-heading text-lg font-bold tracking-tight text-sidebar-foreground">ClawScout</span>
              <span className="ml-1.5 rounded-md bg-violet-50 dark:bg-violet-950/40 px-1.5 py-0.5 text-[10px] font-medium text-violet-600 dark:text-violet-400">v2</span>
            </div>
            <button
              onClick={toggleSidebar}
              className="ml-auto rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              title="Minimizar sidebar"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          </>
        )}
      </div>

      {/* Navigation */}
      <nav className={cn("flex-1 space-y-1 py-4", collapsed ? "px-2" : "px-3")}>
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center rounded-xl text-sm font-medium font-heading transition-all duration-150",
                collapsed ? "justify-center px-0 py-2.5" : "gap-3 px-3 py-2.5",
                isActive
                  ? "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className={cn("h-[18px] w-[18px] shrink-0", isActive ? "text-violet-600 dark:text-violet-400" : "")} />
              {!collapsed && item.label}
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
                "relative flex items-center rounded-xl text-sm font-medium font-heading transition-all duration-150",
                collapsed ? "justify-center px-0 py-2.5" : "gap-3 px-3 py-2.5",
                isActive
                  ? "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className={cn("h-[18px] w-[18px] shrink-0", isActive ? "text-violet-600 dark:text-violet-400" : "")} />
              {!collapsed && <span className="flex-1">{item.label}</span>}
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
      {!collapsed && (
        <div className="border-t border-sidebar-border">
          <ActivityPulse />
        </div>
      )}

      {/* Footer */}
      <div className={cn("border-t border-sidebar-border space-y-1", collapsed ? "p-2" : "p-3")}>
        {!collapsed && <ThemeToggle />}
        <button
          onClick={toggleChat}
          title={collapsed ? "Chat IA" : undefined}
          className={cn(
            "flex w-full items-center rounded-xl text-sm font-medium font-heading transition-all duration-150",
            collapsed ? "justify-center py-2.5" : "gap-3 px-3 py-2.5",
            chatOpen
              ? "bg-violet-600 text-white"
              : "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300 hover:bg-violet-100 dark:hover:bg-violet-950/60"
          )}
        >
          <Sparkles className="h-[18px] w-[18px] shrink-0" />
          {!collapsed && "Chat IA"}
        </button>
        <Link
          href="/settings"
          title={collapsed ? "Configuración" : undefined}
          className={cn(
            "flex items-center rounded-xl text-sm font-medium text-muted-foreground transition-all hover:bg-muted hover:text-foreground",
            collapsed ? "justify-center py-2.5" : "gap-3 px-3 py-2.5"
          )}
        >
          <Settings className="h-[18px] w-[18px] shrink-0" />
          {!collapsed && "Configuración"}
        </Link>
      </div>
    </aside>
  );
}
