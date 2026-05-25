import { apiPost } from "./client";

export interface HoldingAdjustment {
  entity_type: string;
  entity_code: string;
  entity_name: string;
  current_mv: string;
  current_temp: string;
  suggested_mv: string;
  delta_mv: string;
  direction: "ADD" | "REDUCE" | "HOLD";
}

export interface RebalanceSuggestResponse {
  feasible: boolean;
  current_temp: string | null;
  target_temp: string;
  projected_temp: string | null;
  total_mv: string;
  adjustments: HoldingAdjustment[];
  notes: string[];
}

export function rebalanceSuggest(
  target: number,
  tolerance = 2,
): Promise<RebalanceSuggestResponse> {
  return apiPost("/holdings/rebalance-suggest", {
    target_temperature: target,
    tolerance,
  });
}
