import { apiPost } from "./client";
export function rebalanceSuggest(target, tolerance = 2) {
    return apiPost("/holdings/rebalance-suggest", {
        target_temperature: target,
        tolerance,
    });
}
