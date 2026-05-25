import { apiGet } from "./client";
export function search(q, types, limit = 20) {
    const params = new URLSearchParams();
    params.set("q", q);
    if (types && types.length > 0)
        params.set("types", types.join(","));
    params.set("limit", String(limit));
    return apiGet(`/search?${params.toString()}`);
}
