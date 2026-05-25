import { apiGet } from "./client";
export function fetchOpportunities() {
    return apiGet("/opportunities");
}
export function fetchTierTransitions(days = 7) {
    return apiGet(`/tier-transitions?days=${days}`);
}
