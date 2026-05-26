import { apiPost } from "./client";
export function rebalanceSuggest(reduce_pct = 0.30) {
    return apiPost("/holdings/rebalance-suggest", { reduce_pct });
}
