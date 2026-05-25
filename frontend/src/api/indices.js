import { apiGet } from "./client";
export function fetchIndexDetail(code, peSource = "lg") {
    return apiGet(`/indices/${encodeURIComponent(code)}/detail?pe_source=${peSource}`);
}
