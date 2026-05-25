import { apiGet } from "./client";
import type { OverviewResponse } from "@/types/api";

export function fetchOverview(peSource: "lg" | "csi" = "lg"): Promise<OverviewResponse> {
  return apiGet<OverviewResponse>(`/overview?pe_source=${peSource}`);
}
