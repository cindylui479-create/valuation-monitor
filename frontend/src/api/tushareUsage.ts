import { apiGet } from "./client";

export interface InterfaceStat {
  interface: string;
  n_calls: number;
  n_failures: number;
  last_error_message: string | null;
}

export interface DailyStat {
  date: string;
  n_calls: number;
  n_failures: number;
}

export interface TushareUsageResponse {
  today: {
    date: string;
    total_calls: number;
    total_failures: number;
    by_interface: InterfaceStat[];
  };
  month: {
    month_start: string;
    total_calls: number;
    total_failures: number;
  };
  last_30_days: DailyStat[];
  by_interface_30d: InterfaceStat[];
}

export function fetchTushareUsage(): Promise<TushareUsageResponse> {
  return apiGet<TushareUsageResponse>("/tushare-usage");
}
