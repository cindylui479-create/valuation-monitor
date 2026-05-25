import { apiGet } from "./client";

export interface PipelineRunDay {
  date: string;
  market: string;
  quotes_upserted: number;
  audits_logged: number;
  signals_generated: number;
  dca_executions_generated: number;
  first_event_at: string | null;
  last_event_at: string | null;
}

export interface PipelineRunsResponse {
  items: PipelineRunDay[];
  days: number;
}

export function fetchPipelineRuns(days = 30): Promise<PipelineRunsResponse> {
  return apiGet<PipelineRunsResponse>(`/pipeline-runs?days=${days}`);
}
