import { apiDelete, apiGet, apiPut } from "./client";
export function fetchOverride(index_code) {
    return apiGet(`/threshold-overrides/${encodeURIComponent(index_code)}`);
}
export function putOverride(index_code, body) {
    return apiPut(`/threshold-overrides/${encodeURIComponent(index_code)}`, body);
}
export function deleteOverride(index_code) {
    return apiDelete(`/threshold-overrides/${encodeURIComponent(index_code)}`);
}
