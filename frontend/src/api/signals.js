import { apiGet } from "./client";
export function fetchTodaySignals(onlySubscribed = false, peSource = "lg") {
    const q = new URLSearchParams();
    q.set("pe_source", peSource);
    if (onlySubscribed)
        q.set("only_subscribed", "true");
    return apiGet(`/signals/today?${q.toString()}`);
}
export function fetchSignals(params) {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
        if (v != null && v !== "")
            q.set(k, String(v));
    }
    if (!q.get("pe_source"))
        q.set("pe_source", "lg");
    return apiGet(`/signals?${q.toString()}`);
}
