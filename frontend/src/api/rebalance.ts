import { apiPost } from "./client";

export interface HoldingAdjustment {
  entity_type: string;
  entity_code: string;
  entity_name: string;
  current_mv: string;
  current_temp: string;
  tier: string | null;
  suggested_mv: string;
  delta_mv: string;
  direction: "ADD" | "REDUCE" | "HOLD";
  bucket: "HIGH" | "LOW" | "MID";
}

export interface RebalanceSuggestResponse {
  feasible: boolean;
  reduce_pct: string;
  current_temp: string | null;
  projected_temp: string | null;
  total_mv: string;
  total_released: string;
  n_high: number;
  n_low: number;
  n_mid: number;
  adjustments: HoldingAdjustment[];
  notes: string[];
}

export function rebalanceSuggest(reduce_pct = 0.30): Promise<RebalanceSuggestResponse> {
  return apiPost("/holdings/rebalance-suggest", { reduce_pct });
}
