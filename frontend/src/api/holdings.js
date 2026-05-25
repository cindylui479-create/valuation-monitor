import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
export function fetchPortfolio() {
    return apiGet("/holdings");
}
export function addHolding(body) {
    return apiPost("/holdings", body);
}
export function updateHolding(id, body) {
    return apiPatch(`/holdings/${id}`, body);
}
export function deleteHolding(id) {
    return apiDelete(`/holdings/${id}`);
}
