"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark" | "system";

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resolved: "light" | "dark";
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "system",
  setTheme: () => {},
  resolved: "light",
});

export function useTheme() {
  return useContext(ThemeContext);
}

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("system");
  const [resolved, setResolved] = useState<"light" | "dark">("light");

  // Hydrate theme from localStorage on mount — canonical sync of external
  // state (storage) into React state. The setState IS the purpose of the effect.
  useEffect(() => {
    const stored = localStorage.getItem("scouter-theme") as Theme | null;
    if (stored) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setThemeState(stored);
    }
  }, []);

  // Derived theme resolution + DOM class + localStorage persistence. setResolved
  // is a valid sync of computed state (system theme or explicit).
  useEffect(() => {
    const root = document.documentElement;
    const res = theme === "system" ? getSystemTheme() : theme;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setResolved(res);

    root.classList.toggle("dark", res === "dark");

    if (theme !== "system") {
      localStorage.setItem("scouter-theme", theme);
    } else {
      localStorage.removeItem("scouter-theme");
    }
  }, [theme]);

  useEffect(() => {
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      const res = getSystemTheme();
      setResolved(res);
      document.documentElement.classList.toggle("dark", res === "dark");
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  function setTheme(t: Theme) {
    setThemeState(t);
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolved }}>
      {children}
    </ThemeContext.Provider>
  );
}
