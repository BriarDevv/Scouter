"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import {
  Inbox,
  LayoutDashboard,
  Users,
  Mail,
  BarChart3,
  ShieldOff,
  Radar,
  Settings,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/",            label: "Panel general", icon: LayoutDashboard },
  { href: "/leads",       label: "Leads",         icon: Users },
  { href: "/outreach",    label: "Outreach",      icon: Mail },
  { href: "/responses",   label: "Respuestas",    icon: Inbox },
  { href: "/performance", label: "Rendimiento",   icon: BarChart3 },
  { href: "/suppression", label: "Supresión",     icon: ShieldOff },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-sidebar-border bg-sidebar">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600">
          <Radar className="h-4.5 w-4.5 text-white" />
        </div>
        <div>
          <span className="font-heading text-lg font-bold tracking-tight text-sidebar-foreground">ClawScout</span>
          <span className="ml-1.5 rounded-md bg-violet-50 dark:bg-violet-950/40 px-1.5 py-0.5 text-[10px] font-medium text-violet-600 dark:text-violet-400">v1</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium font-heading transition-all duration-150",
                isActive
                  ? "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className={cn("h-[18px] w-[18px]", isActive ? "text-violet-600 dark:text-violet-400" : "")} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border p-3 space-y-1">
        <ThemeToggle />
        <Link
          href="/settings"
          className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground transition-all hover:bg-muted hover:text-foreground"
        >
          <Settings className="h-[18px] w-[18px]" />
          Configuración
        </Link>
      </div>
    </aside>
  );
}
