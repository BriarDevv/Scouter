"use client";
import useSWR, { type SWRConfiguration } from "swr";
import { apiFetch } from "@/lib/api/client";

export function useApi<T>(url: string | null, config?: SWRConfiguration) {
  return useSWR<T>(url, (u) => apiFetch<T>(u), {
    revalidateOnFocus: false,
    ...config,
  });
}
