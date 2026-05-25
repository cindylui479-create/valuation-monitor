import { apiGet } from "./client";

export interface SourceStatus {
  name: string;
  last_success_at: string | null;
  last_error_at: string | null;
  last_error_message?: string | null;
}

export interface PipelineStatus {
  market: string;
  last_run_at: string | null;
  status: string;
  duration_seconds: number | null;
  errors: string[];
}

export interface HealthResponse {
  sources: SourceStatus[];
  pipeline: PipelineStatus[];
}

export function fetchHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health");
}
