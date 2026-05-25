export interface OverviewIndex {
  code: string;
  name: string;
  category: string;
  tier: string | null;
  temperature: string | null;
  pe_ttm: string | null;
  pe_percentile_10y: string | null;
  pb_percentile_10y: string | null;
  dividend_yield: string | null;
  ma50_deviation: string | null;
  ma200_deviation: string | null;
  data_window_note: string | null;
  temperature_source: string | null;
  funds_count: number;
}

export interface OverviewMarket {
  market: string;
  currency: string;
  indices: OverviewIndex[];
}

export interface OverviewResponse {
  as_of: string | null;
  markets: OverviewMarket[];
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}

export interface FundDTO {
  code: string;
  name: string;
  type: string;
  fee_rate: string | null;
  tracking_error_note: string | null;
}

export interface QuotePoint {
  date: string;
  close: string;
  pe_ttm: string | null;
  pb: string | null;
  dividend_yield: string | null;
}

export interface ValuationPoint {
  date: string;
  pe_percentile: string | null;
  pb_percentile: string | null;
  temperature: string | null;
  tier: string | null;
  temperature_source?: string | null;
}

export interface SignalPoint {
  date: string;
  direction: "STRONG_BUY" | "BUY" | "SELL" | "STRONG_SELL";
  tier: string;
  temperature: string;
}

export interface IndexDetail {
  code: string;
  name: string;
  market: string;
  currency: string;
  category: string;
  industry_raw: string | null;
  history_start_date: string;
  actual_history_years: number;
  data_window_note: string | null;
  enabled: boolean;
  funds: FundDTO[];
  latest_valuation: ValuationPoint | null;
  latest_signal: SignalPoint | null;
  signal_history: SignalPoint[];
  quotes: QuotePoint[];
  valuation_series: ValuationPoint[];
}

export interface WatchlistItem {
  id: number;
  index_code: string;
  index_name: string;
  market: string | null;
  category: string | null;
  industry_raw: string | null;
  tag: string | null;
  added_at: string;
  temperature: string | null;
  tier: string | null;
  pe_ttm: string | null;
  pb: string | null;
  dividend_yield: string | null;
  valuation_source: string | null;
  temperature_source: string | null;
  actual_history_years: number | null;
  data_window_note: string | null;
}

export interface Boundaries {
  extreme_low_upper: string | null;
  low_upper: string | null;
  high_lower: string | null;
  extreme_high_lower: string | null;
}

export interface ThresholdOverrideResponse {
  index_code: string;
  boundaries: {
    extreme_low_upper: string;
    low_upper: string;
    high_lower: string;
    extreme_high_lower: string;
  };
  is_default: boolean;
  updated_at: string | null;
}

export interface SignalDTO {
  id: number;
  index_code: string;
  index_name: string;
  market: string;
  date: string;
  direction: "STRONG_BUY" | "BUY" | "SELL" | "STRONG_SELL";
  tier: string;
  temperature: string;
  generated_at: string;
}

export interface SignalListResponse {
  items: SignalDTO[];
  total: number;
}

export interface DCAPlanDTO {
  id: number;
  index_code: string;
  index_name: string;
  fund_code: string | null;
  fund_name: string | null;
  amount: string;
  frequency: "WEEKLY" | "BIWEEKLY" | "MONTHLY";
  day_of_period: number;
  start_date: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface DCAExecutionDTO {
  id: number;
  plan_id: number;
  index_code: string;
  index_name: string;
  scheduled_date: string;
  actual_date: string;
  base_amount: string;
  adjusted_amount: string;
  multiplier: string;
  tier_at_decision: string;
  temperature: string;
  status: "PENDING" | "DONE" | "SKIPPED";
  generated_at: string;
  marked_at: string | null;
}

export interface UpcomingReminderResponse {
  items: DCAExecutionDTO[];
}

export interface BacktestTradeDTO {
  date: string;
  action: "BUY" | "SELL" | "DCA_BUY";
  price: string;
  pe_percentile: string | null;
  amount: string;
  multiplier: string | null;
}

export interface NAVPointDTO {
  date: string;
  nav: string;
}

export interface StrategyResultDTO {
  name: "threshold" | "dca" | "buy_hold";
  annualized_return: string;
  max_drawdown: string;
  final_nav: string;
  trade_count: number;
  trades: BacktestTradeDTO[];
  nav_curve: NAVPointDTO[];
}

export interface BacktestResponse {
  index_code: string;
  index_name: string;
  start_date: string;
  end_date: string;
  buy_percentile_below: string;
  sell_percentile_above: string;
  fee_rate: string;
  slippage_rate: string;
  reinvest_dividend: boolean;
  threshold: StrategyResultDTO;
  dca: StrategyResultDTO | null;
  buy_hold: StrategyResultDTO;
}
