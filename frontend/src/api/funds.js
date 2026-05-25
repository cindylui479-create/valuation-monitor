import { apiDelete, apiGet, apiPost } from "./client";
export function listFunds() {
    return apiGet("/funds");
}
export function fetchFundDetail(code) {
    return apiGet(`/funds/${encodeURIComponent(code)}/detail`);
}
export function addActiveFund(code) {
    return apiPost("/funds/add", { code });
}
export function removeActiveFund(code) {
    return apiDelete(`/funds/${encodeURIComponent(code)}`);
}
