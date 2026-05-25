import { apiGet, apiPatch } from "./client";

export interface IndexAnomalyCount {
  code: string;
  name: string;
  market: string;
  high: number;
  medium: number;
  low: number;
  info: number;
  total: number;
  acknowledged: number;
  latest_anomaly_date: string | null;
}

export interface DataQualitySummary {
  items: IndexAnomalyCount[];
  total_anomalies: number;
}

export interface AnomalyItem {
  id: number;
  date: string;
  field: string;
  source: string;
  anomaly_type: string;
  severity: string;
  value: string | null;
  baseline: string | null;
  note: string | null;
  detected_at: string;
  acknowledged_at: string | null;
  acknowledged_note: string | null;
}

export interface AckResponse {
  id: number;
  acknowledged_at: string | null;
  acknowledged_note: string | null;
}

export interface IndexAnomalyDetail {
  code: string;
  name: string;
  market: string;
  counts: Record<string, number>;
  anomalies: AnomalyItem[];
}

export function fetchDataQualitySummary(
  includeAcknowledged = false,
): Promise<DataQualitySummary> {
  const q = includeAcknowledged ? "?include_acknowledged=true" : "";
  return apiGet<DataQualitySummary>(`/data-quality/summary${q}`);
}

export function fetchDataQualityDetail(code: string): Promise<IndexAnomalyDetail> {
  return apiGet<IndexAnomalyDetail>(`/data-quality/${encodeURIComponent(code)}`);
}

export function setAnomalyAck(
  anomalyId: number,
  acknowledged: boolean,
  note?: string,
): Promise<AckResponse> {
  return apiPatch<AckResponse>(`/data-quality/anomaly/${anomalyId}`, {
    acknowledged,
    note: note ?? null,
  });
}
