import { apiDelete, apiGet, apiPut } from "./client";
import type { Boundaries, ThresholdOverrideResponse } from "@/types/api";

export function fetchOverride(
  index_code: string,
): Promise<ThresholdOverrideResponse> {
  return apiGet<ThresholdOverrideResponse>(
    `/threshold-overrides/${encodeURIComponent(index_code)}`,
  );
}

export function putOverride(
  index_code: string,
  body: Boundaries,
): Promise<ThresholdOverrideResponse> {
  return apiPut<ThresholdOverrideResponse>(
    `/threshold-overrides/${encodeURIComponent(index_code)}`,
    body,
  );
}

export function deleteOverride(index_code: string): Promise<void> {
  return apiDelete(`/threshold-overrides/${encodeURIComponent(index_code)}`);
}
