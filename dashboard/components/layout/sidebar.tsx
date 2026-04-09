"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { ActivityPulse } from "@/components/layout/activity-pulse";
import { getNotificationCounts } from "@/lib/api/client";
import { useChatPanel } from "@/lib/hooks/use-chat-panel";
import { useVisibleInterval } from "@/lib/hooks/use-visible-interval";
import {
  Bell,
  Brain,
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
  MapPin,
  Settings,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/",            label: "Mote",        icon: Sparkles },
  { href: "/panel",       label: "Panel",       icon: LayoutDashboard },
  { href: "/leads",       label: "Leads",       icon: Users },
  { href: "/outreach",    label: "Outreach",    icon: Mail },
  { href: "/responses",   label: "Respuestas",  icon: Inbox },
  { href: "/performance", label: "Rendimiento", icon: BarChart3 },
  { href: "/map",         label: "Mapa",        icon: MapPin },
  { href: "/suppression", label: "Supresión",   icon: ShieldOff },
  { href: "/ai-office",   label: "AI Office",   icon: Brain },
];

const BOTTOM_NAV_ITEMS = [
  { href: "/notifications", label: "Notificaciones", icon: Bell,        badge: true },
  { href: "/security",      label: "Seguridad",      icon: ShieldAlert, badge: false },
];

const LABEL_HIDDEN = "whitespace-nowrap overflow-hidden opacity-0 max-w-0 transition-all duration-[350ms] ease-in-out";
const LABEL_VISIBLE = "whitespace-nowrap overflow-hidden max-w-[200px] transition-all opacity-100 duration-[350ms] ease-in-out delay-0";

export function Sidebar() {
  const pathname = usePathname();
  const [unreadCount, setUnreadCount] = useState(0);
  const { sidebarCollapsed: collapsed, toggleSidebar } = useChatPanel();

  useVisibleInterval(async () => {
    try {
      const data = await getNotificationCounts();
      setUnreadCount(data.total_unread ?? 0);
    } catch (err) {
      console.error("notification_counts_fetch_failed", err);
    }
  }, 30_000);

  const lbl = collapsed ? LABEL_HIDDEN : LABEL_VISIBLE;

  return (
    <aside
      suppressHydrationWarning
      className={cn(
        "fixed inset-y-0 left-0 z-40 flex flex-col overflow-hidden bg-sidebar",
        "transition-[width] duration-[350ms] ease-in-out",
        collapsed ? "w-[52px]" : "w-52"
      )}
    >
      {/* Header */}
      <div className={cn("flex h-14 items-center border-b border-sidebar-border shrink-0", collapsed ? "px-2.5 justify-center" : "px-3")}>
        <div className={cn(lbl, "flex items-center gap-1.5 min-w-0 flex-1")}>
          <span className="font-heading text-base font-bold tracking-tight text-sidebar-foreground">
            Scouter
          </span>
          <span className="rounded-md bg-muted dark:bg-white/8 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground dark:text-white/60 shrink-0">
            v3
          </span>
        </div>
        <button
          onClick={toggleSidebar}
          className="flex h-8 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          title={collapsed ? "Expandir sidebar" : "Minimizar sidebar"}
        >
          {collapsed
            ? <PanelLeftOpen className="h-4 w-4" />
            : <PanelLeftClose className="h-4 w-4" />
          }
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 px-2 py-3 overflow-y-auto overflow-x-hidden">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          const isMote = item.href === "/";
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center rounded-xl py-2 text-sm font-medium font-heading transition-all duration-[350ms] ease-in-out",
                collapsed ? "px-[9px] gap-0" : "gap-2.5 px-3",
                "border",
                isActive && isMote
                  ? "border-transparent bg-foreground text-background shadow-sm dark:bg-foreground dark:shadow-none"
                  : isActive
                  ? "border-transparent bg-muted dark:bg-white/10 text-foreground dark:text-white"
                  : isMote
                  ? "border-border/60 text-foreground/70 hover:bg-muted hover:border-border mote-shimmer"
                  : "border-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className={cn(
                "h-[18px] w-[18px] shrink-0",
                isActive && isMote ? "text-background" : isActive ? "text-foreground dark:text-white" : !isActive && isMote ? "text-foreground" : ""
              )} />
              <span className={cn(lbl, !isActive && isMote && "text-foreground")}>{item.label}</span>
            </Link>
          );
        })}

        <div className="my-2 border-t border-sidebar-border/60" />

        {BOTTOM_NAV_ITEMS.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={cn(
                "relative flex items-center rounded-xl py-2 text-sm font-medium font-heading transition-all duration-[350ms] ease-in-out",
                collapsed ? "px-[9px] gap-0" : "gap-2.5 px-3",
                isActive
                  ? "bg-muted dark:bg-white/10 text-foreground dark:text-white"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className={cn("h-[18px] w-[18px] shrink-0", isActive ? "text-foreground dark:text-white" : "")} />
              <span className={cn(lbl, "flex-1")}>{item.label}</span>
              {item.badge && unreadCount > 0 && (
                <span className={cn(
                  "bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1",
                  collapsed && "absolute top-0 right-0 min-w-[16px] h-[16px] text-[9px]"
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
        collapsed ? "max-h-0 border-t-0" : "max-h-96"
      )}>
        <ActivityPulse />
      </div>

      {/* Footer */}
      <div className="border-t border-sidebar-border space-y-0.5 p-2 shrink-0">
        <ThemeToggle collapsed={collapsed} />
        <Link
          href="/settings"
          title={collapsed ? "Configuración" : undefined}
          className={cn(
            "flex items-center rounded-xl py-2 text-sm font-medium font-heading transition-all duration-[350ms] ease-in-out",
            collapsed ? "px-[9px] gap-0" : "gap-2.5 px-3",
            pathname.startsWith("/settings")
              ? "bg-muted dark:bg-white/10 text-foreground dark:text-white"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <Settings className={cn("h-[18px] w-[18px] shrink-0", pathname.startsWith("/settings") ? "text-foreground dark:text-foreground" : "")} />
          <span className={lbl}>Configuración</span>
        </Link>
      </div>
    </aside>
  );
}
