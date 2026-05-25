import { apiGet } from "./client";
import type { SignalListResponse } from "@/types/api";

export function fetchTodaySignals(
  onlySubscribed = false, peSource: "lg" | "csi" = "lg",
): Promise<SignalListResponse> {
  const q = new URLSearchParams();
  q.set("pe_source", peSource);
  if (onlySubscribed) q.set("only_subscribed", "true");
  return apiGet<SignalListResponse>(`/signals/today?${q.toString()}`);
}

export function fetchSignals(params: {
  date_from?: string;
  date_to?: string;
  market?: string;
  direction?: string;
  only_subscribed?: boolean;
  limit?: number;
  pe_source?: "lg" | "csi";
}): Promise<SignalListResponse> {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v != null && v !== "") q.set(k, String(v));
  }
  if (!q.get("pe_source")) q.set("pe_source", "lg");
  return apiGet<SignalListResponse>(`/signals?${q.toString()}`);
}
