import { apiGet } from "./client";

export interface SearchHit {
  entity_type: "INDEX" | "STOCK" | "FUND";
  code: string;
  name: string;
  market: string | null;
  extra: string | null;
}

export function search(
  q: string,
  types?: ("INDEX" | "STOCK" | "FUND")[],
  limit = 20,
): Promise<{ items: SearchHit[] }> {
  const params = new URLSearchParams();
  params.set("q", q);
  if (types && types.length > 0) params.set("types", types.join(","));
  params.set("limit", String(limit));
  return apiGet(`/search?${params.toString()}`);
}
