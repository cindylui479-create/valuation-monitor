import { apiDelete, apiGet, apiPatch, apiPost } from "./client";

export interface StockSummary {
  code: string;
  name: string;
  industry: string | null;
  anchor: string;
  listing_date: string | null;
  temperature: string | null;
  tier: string | null;
  pe_ttm: string | null;
  pb: string | null;
  ps_ttm: string | null;
  actual_history_years: number;
  data_window_note: string | null;
}

export interface QuotePoint {
  date: string;
  close: string;
  pe_ttm: string | null;
  pb: string | null;
  ps_ttm: string | null;
  dividend_yield: string | null;
}

export interface StockValuationPoint {
  date: string;
  window: string;
  anchor: string;
  pe_percentile: string | null;
  pb_percentile: string | null;
  ps_percentile: string | null;
  dy_percentile: string | null;
  temperature: string | null;
  tier: string | null;
}

export interface StockDetail {
  code: string;
  name: string;
  industry: string | null;
  anchor: string;
  available_anchors: string[];
  listing_date: string | null;
  status: string;
  actual_history_years: number;
  data_window_note: string | null;
  latest_valuation: StockValuationPoint | null;
  quotes: QuotePoint[];
  valuation_series: StockValuationPoint[];
}

export function listStocks(): Promise<{ items: StockSummary[] }> {
  return apiGet("/stocks");
}

export function addStock(code: string): Promise<StockSummary> {
  return apiPost("/stocks/add", { code });
}

export function fetchStockDetail(code: string): Promise<StockDetail> {
  return apiGet(`/stocks/${encodeURIComponent(code)}/detail`);
}

export function updateStockAnchor(code: string, anchor: string): Promise<StockSummary> {
  return apiPatch(`/stocks/${encodeURIComponent(code)}/anchor`, { anchor });
}

export function removeStock(code: string): Promise<void> {
  return apiDelete(`/stocks/${encodeURIComponent(code)}`);
}
