import { apiPost } from "./client";
import type { BacktestResponse } from "@/types/api";

export interface BacktestRequest {
  index_code: string;
  buy_percentile_below: string;
  sell_percentile_above: string;
  start_date?: string;
  end_date?: string;
  window?: "5y" | "10y" | "all";
  fee_rate?: string;
  slippage_rate?: string;
  reinvest_dividend?: boolean;
  include_dca?: boolean;
}

export function runBacktest(body: BacktestRequest): Promise<BacktestResponse> {
  return apiPost<BacktestResponse>("/backtest/run", body);
}

export function exportCsvUrl(indexCode: string, window: "5y" | "10y" | "all" = "10y"): string {
  return `/api/v1/exports/index/${encodeURIComponent(indexCode)}.csv?window=${window}`;
}
