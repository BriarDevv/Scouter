"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
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
  { href: "/",            label: "Overview",     icon: LayoutDashboard },
  { href: "/leads",       label: "Leads",        icon: Users },
  { href: "/outreach",    label: "Outreach",     icon: Mail },
  { href: "/responses",   label: "Responses",    icon: Inbox },
  { href: "/performance", label: "Rendimiento",  icon: BarChart3 },
  { href: "/suppression", label: "Supresión",    icon: ShieldOff },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200/80 bg-white">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-slate-100 px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600">
          <Radar className="h-4.5 w-4.5 text-white" />
        </div>
        <div>
          <span className="font-heading text-lg font-bold tracking-tight text-slate-900">ClawScout</span>
          <span className="ml-1.5 rounded-md bg-violet-50 px-1.5 py-0.5 text-[10px] font-medium text-violet-600">v1</span>
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
                  ? "bg-violet-50 text-violet-700"
                  : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
              )}
            >
              <item.icon className={cn("h-[18px] w-[18px]", isActive ? "text-violet-600" : "text-slate-400")} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-100 p-3">
        <Link
          href="/settings"
          className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-500 transition-all hover:bg-slate-50 hover:text-slate-900"
        >
          <Settings className="h-[18px] w-[18px] text-slate-400" />
          Configuración
        </Link>
      </div>
    </aside>
  );
}
