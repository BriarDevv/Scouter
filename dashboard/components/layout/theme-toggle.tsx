"use client";

import { Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "@/components/providers/theme-provider";
import { cn } from "@/lib/utils";

const CYCLE: Array<"light" | "dark" | "system"> = ["light", "dark", "system"];

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  function cycle() {
    const idx = CYCLE.indexOf(theme);
    setTheme(CYCLE[(idx + 1) % CYCLE.length]);
  }

  const Icon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;

  return (
    <button
      onClick={cycle}
      className={cn(
        "flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
        "text-muted-foreground hover:bg-muted hover:text-foreground"
      )}
      title={`Tema: ${theme === "light" ? "Claro" : theme === "dark" ? "Oscuro" : "Sistema"}`}
    >
      <Icon className="h-[18px] w-[18px]" />
      <span className="text-xs">{theme === "light" ? "Claro" : theme === "dark" ? "Oscuro" : "Sistema"}</span>
    </button>
  );
}
