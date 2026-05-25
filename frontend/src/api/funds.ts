import { apiDelete, apiGet, apiPost } from "./client";

export interface FundSummary {
  code: string;
  name: string;
  type: string;
  fund_type: string;                // ETF / INDEX_FUND / ACTIVE_FUND
  market: string;
  fee_rate: string | null;
  tracking_error_note: string | null;
  setup_date: string | null;
  fund_manager: string | null;
  tracks_index_code: string | null;
  tracks_index_name: string | null;
  temperature: string | null;
  tier: string | null;
  pe_ttm: string | null;
  pb: string | null;
  valuation_source: string | null;  // index_lg / index_csi / nav_5y / null
  nav_latest: string | null;
  actual_history_years: number | null;
  data_window_note: string | null;
}

export interface FundListResponse {
  items: FundSummary[];
}

export interface NAVPoint {
  date: string;
  nav: string;
}

export interface FundValuationPoint {
  date: string;
  window: string;
  nav_percentile: string | null;
  temperature: string | null;
  tier: string | null;
}

export interface FundDetail {
  code: string;
  name: string;
  fund_type: string;
  fund_manager: string | null;
  setup_date: string | null;
  market: string;
  tracks_index_code: string | null;
  tracks_index_name: string | null;
  actual_history_years: number;
  data_window_note: string | null;
  latest_valuation: FundValuationPoint | null;
  nav_history: NAVPoint[];
  valuation_series: FundValuationPoint[];
}

export function listFunds(): Promise<FundListResponse> {
  return apiGet<FundListResponse>("/funds");
}

export function fetchFundDetail(code: string): Promise<FundDetail> {
  return apiGet<FundDetail>(`/funds/${encodeURIComponent(code)}/detail`);
}

export function addActiveFund(code: string): Promise<FundSummary> {
  return apiPost<FundSummary>("/funds/add", { code });
}

export function removeActiveFund(code: string): Promise<void> {
  return apiDelete(`/funds/${encodeURIComponent(code)}`);
}
