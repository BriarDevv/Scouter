"use client";
import { useCallback, useEffect, useRef } from "react";

export function useVisibleInterval(callback: () => void, intervalMs: number) {
  const savedCallback = useRef(callback);
  savedCallback.current = callback;

  useEffect(() => {
    if (typeof document === "undefined") return;
    let timer: ReturnType<typeof setInterval> | null = null;

    function start() {
      if (!timer) {
        savedCallback.current();
        timer = setInterval(() => savedCallback.current(), intervalMs);
      }
    }
    function stop() {
      if (timer) { clearInterval(timer); timer = null; }
    }
    function onChange() { document.hidden ? stop() : start(); }

    document.addEventListener("visibilitychange", onChange);
    if (!document.hidden) start();
    return () => { stop(); document.removeEventListener("visibilitychange", onChange); };
  }, [intervalMs]);
}
