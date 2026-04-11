"use client";
import { useEffect, useRef } from "react";

export function useVisibleInterval(callback: () => void, intervalMs: number) {
  const savedCallback = useRef(callback);

  // Sync the latest callback into the ref without writing during render.
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

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
    function onChange() {
      if (document.hidden) {
        stop();
      } else {
        start();
      }
    }

    document.addEventListener("visibilitychange", onChange);
    if (!document.hidden) start();
    return () => { stop(); document.removeEventListener("visibilitychange", onChange); };
  }, [intervalMs]);
}
