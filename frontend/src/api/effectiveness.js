import { apiGet } from "./client";
export function fetchEffectiveness(horizon = 90, years = 10, indexCode) {
    const p = new URLSearchParams();
    p.set("horizon", String(horizon));
    p.set("years", String(years));
    if (indexCode)
        p.set("index_code", indexCode);
    return apiGet(`/temperature/effectiveness?${p.toString()}`);
}
