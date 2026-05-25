import { apiDelete, apiGet, apiPatch, apiPost } from "./client";

export type EntityType = "INDEX" | "STOCK" | "FUND";

export interface HoldingItem {
  id: number;
  entity_type: EntityType;
  entity_code: string;
  entity_name: string | null;
  market_value: string;
  quantity: string | null;
  latest_price: string | null;
  input_mode: "value" | "quantity";
  weight_pct: string | null;
  temperature: string | null;
  tier: string | null;
  temperature_source: string | null;
  pe_ttm: string | null;
  pb: string | null;
  note: string | null;
  added_at: string;
  updated_at: string;
}

export interface PortfolioSummary {
  total_value: string;
  weighted_temperature: string | null;
  valued_value: string;
  coverage_pct: string;
  tier_distribution: Record<string, string>;
  items: HoldingItem[];
}

export function fetchPortfolio(): Promise<PortfolioSummary> {
  return apiGet<PortfolioSummary>("/holdings");
}

export function addHolding(body: {
  entity_type: EntityType;
  entity_code: string;
  market_value?: number;
  quantity?: number;
  note?: string;
}): Promise<HoldingItem> {
  return apiPost<HoldingItem>("/holdings", body);
}

export function updateHolding(
  id: number,
  body: { market_value?: number; quantity?: number; note?: string },
): Promise<HoldingItem> {
  return apiPatch<HoldingItem>(`/holdings/${id}`, body);
}

export function deleteHolding(id: number): Promise<void> {
  return apiDelete(`/holdings/${id}`);
}
