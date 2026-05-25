import { apiGet } from "./client";

export interface BucketStats {
  tier: string;
  temp_range: string;
  n_samples: number;
  median_return_pct: string | null;
  mean_return_pct: string | null;
  p25: string | null;
  p75: string | null;
  p10: string | null;
  p90: string | null;
  win_rate: string | null;
}

export interface FineBucketPoint {
  temp_center: number;
  n_samples: number;
  median_return_pct: string | null;
}

export interface IndexCoverage {
  code: string;
  name: string;
  n_samples: number;
}

export interface IndexEffectiveness {
  code: string;
  name: string;
  n_samples: number;
  spearman_ic: string | null;
  low_temp_median_return: string | null;
  high_temp_median_return: string | null;
  edge_pct: string | null;
}

export interface EffectivenessResponse {
  horizon_days: number;
  years: number;
  scope: string;
  total_samples: number;
  coarse_buckets: BucketStats[];
  fine_buckets: FineBucketPoint[];
  indices_coverage: IndexCoverage[];
  spearman_ic: string | null;
  by_index_effectiveness: IndexEffectiveness[];
}

export function fetchEffectiveness(
  horizon = 90,
  years = 10,
  indexCode?: string,
): Promise<EffectivenessResponse> {
  const p = new URLSearchParams();
  p.set("horizon", String(horizon));
  p.set("years", String(years));
  if (indexCode) p.set("index_code", indexCode);
  return apiGet(`/temperature/effectiveness?${p.toString()}`);
}
