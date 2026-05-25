import { apiGet } from "./client";
import type { IndexDetail } from "@/types/api";

export function fetchIndexDetail(
  code: string, peSource: "lg" | "csi" = "lg",
): Promise<IndexDetail> {
  return apiGet<IndexDetail>(
    `/indices/${encodeURIComponent(code)}/detail?pe_source=${peSource}`,
  );
}
