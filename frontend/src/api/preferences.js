import { apiGet, apiPut } from "./client";
export function fetchPreferences() {
    return apiGet("/preferences");
}
export function updatePreferences(p) {
    return apiPut("/preferences", p);
}
