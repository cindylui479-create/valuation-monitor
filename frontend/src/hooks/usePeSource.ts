import { useQuery } from "@tanstack/react-query";
import { fetchPreferences } from "@/api/preferences";

/**
 * SRS R10：全局 PE 口径偏好（lg / csi）。
 * 所有数据请求的 queryKey 应包含此值，切换偏好后自动重取所有数据。
 */
export function usePeSource(): "lg" | "csi" {
  const { data } = useQuery({
    queryKey: ["preferences"],
    queryFn: fetchPreferences,
    staleTime: 60_000,
  });
  return data?.pe_source ?? "lg";
}
