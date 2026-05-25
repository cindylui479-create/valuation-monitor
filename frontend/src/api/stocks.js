import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
export function listStocks() {
    return apiGet("/stocks");
}
export function addStock(code) {
    return apiPost("/stocks/add", { code });
}
export function fetchStockDetail(code) {
    return apiGet(`/stocks/${encodeURIComponent(code)}/detail`);
}
export function updateStockAnchor(code, anchor) {
    return apiPatch(`/stocks/${encodeURIComponent(code)}/anchor`, { anchor });
}
export function removeStock(code) {
    return apiDelete(`/stocks/${encodeURIComponent(code)}`);
}
