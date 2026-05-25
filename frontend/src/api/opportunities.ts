import { apiGet } from "./client";

export interface Opportunity {
  entity_type: "INDEX" | "STOCK" | "FUND";
  entity_code: string;
  entity_name: string;
  market: string | null;
  temperature: string;
  tier: string;
  temperature_source: string | null;
  pe_ttm: string | null;
  pb: string | null;
}

export interface OpportunitiesResponse {
  low_valuations: Opportunity[];
  high_valuations: Opportunity[];
  total: number;
}

export interface TierTransition {
  entity_type: "INDEX" | "STOCK" | "FUND";
  entity_code: string;
  entity_name: string;
  date: string;
  from_tier: string | null;
  to_tier: string;
  from_temperature: string | null;
  to_temperature: string;
  temperature_delta: string;
  severity: "HIGH" | "MEDIUM" | "INFO";
  direction: "up" | "down";
}

export interface TierTransitionsResponse {
  days: number;
  items: TierTransition[];
}

export function fetchOpportunities(): Promise<OpportunitiesResponse> {
  return apiGet<OpportunitiesResponse>("/opportunities");
}

export function fetchTierTransitions(days = 7): Promise<TierTransitionsResponse> {
  return apiGet<TierTransitionsResponse>(`/tier-transitions?days=${days}`);
}
