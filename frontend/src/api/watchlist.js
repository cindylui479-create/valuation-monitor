import { apiDelete, apiGet, apiPost } from "./client";
export function fetchWatchlist(peSource = "lg") {
    return apiGet(`/watchlist?pe_source=${peSource}`);
}
export function addToWatchlist(index_code, tag) {
    return apiPost("/watchlist", { index_code, tag: tag ?? null });
}
export function removeFromWatchlist(id) {
    return apiDelete(`/watchlist/${id}`);
}
