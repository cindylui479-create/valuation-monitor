import { apiGet, apiPut } from "./client";

export interface Preferences {
  default_window: "5y" | "10y" | "all";
  theme: "light" | "dark";
  overview_default_filter: string;
  pe_source: "lg" | "csi";
}

export function fetchPreferences(): Promise<Preferences> {
  return apiGet<Preferences>("/preferences");
}

export function updatePreferences(p: Partial<Preferences>): Promise<Preferences> {
  return apiPut<Preferences>("/preferences", p);
}
