import { apiGet } from "./client";
export function fetchOverview(peSource = "lg") {
    return apiGet(`/overview?pe_source=${peSource}`);
}
