"use client";

import { Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "@/components/providers/theme-provider";
import { cn } from "@/lib/utils";

const CYCLE: Array<"light" | "dark" | "system"> = ["light", "dark", "system"];
const LABEL = { light: "Claro", dark: "Oscuro", system: "Sistema" } as const;

export function ThemeToggle({ collapsed = false }: { collapsed?: boolean }) {
  const { theme, setTheme } = useTheme();

  function cycle() {
    const idx = CYCLE.indexOf(theme);
    setTheme(CYCLE[(idx + 1) % CYCLE.length]);
  }

  const Icon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;

  return (
    <button
      onClick={cycle}
      title={`Tema: ${LABEL[theme]}`}
      className={cn(
        "w-full flex items-center rounded-xl py-2 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground",
        "transition-all duration-[350ms] ease-in-out",
        collapsed ? "px-[9px] gap-0" : "gap-3 px-3"
      )}
    >
      <Icon className="h-[18px] w-[18px] shrink-0" />
      <span className={cn(
        "whitespace-nowrap overflow-hidden text-xs transition-all duration-[350ms] ease-in-out",
        collapsed
          ? "opacity-0 max-w-0"
          : "opacity-100 max-w-[200px]"
      )}>
        {LABEL[theme]}
      </span>
    </button>
  );
}
