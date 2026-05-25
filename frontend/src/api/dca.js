import { apiDelete, apiGet, apiPost, apiPut } from "./client";
export function fetchDCAPlans() {
    return apiGet("/dca-plans");
}
export function createDCAPlan(body) {
    return apiPost("/dca-plans", body);
}
export function updateDCAPlan(id, body) {
    return apiPut(`/dca-plans/${id}`, body);
}
export function deleteDCAPlan(id) {
    return apiDelete(`/dca-plans/${id}`);
}
export function fetchExecutions(planId) {
    return apiGet(`/dca-plans/${planId}/executions`);
}
export function fetchUpcoming(within = 7) {
    return apiGet(`/dca-reminders/upcoming?within_days=${within}`);
}
export function markDone(execId) {
    return apiPost(`/dca-executions/${execId}/mark-done`, {});
}
export function markSkipped(execId) {
    return apiPost(`/dca-executions/${execId}/skip`, {});
}
export function fetchDCAStats() {
    return apiGet("/dca-plans/stats");
}
