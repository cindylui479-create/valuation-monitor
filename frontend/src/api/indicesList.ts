import { apiGet } from "./client";

export interface IndexLite {
  code: string;
  name: string;
  market: string;
  category: string;
  enabled: boolean;
}

export function fetchIndicesList(): Promise<IndexLite[]> {
  return apiGet<IndexLite[]>("/indices");
}
