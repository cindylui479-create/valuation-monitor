import { apiDelete, apiGet, apiPost } from "./client";
import type { WatchlistItem } from "@/types/api";

export function fetchWatchlist(peSource: "lg" | "csi" = "lg"): Promise<WatchlistItem[]> {
  return apiGet<WatchlistItem[]>(`/watchlist?pe_source=${peSource}`);
}

export function addToWatchlist(
  index_code: string,
  tag?: string | null,
): Promise<WatchlistItem> {
  return apiPost<WatchlistItem>("/watchlist", { index_code, tag: tag ?? null });
}

export function removeFromWatchlist(id: number): Promise<void> {
  return apiDelete(`/watchlist/${id}`);
}
