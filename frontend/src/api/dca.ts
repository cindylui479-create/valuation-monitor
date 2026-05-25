import { apiDelete, apiGet, apiPost, apiPut } from "./client";
import type {
  DCAExecutionDTO,
  DCAPlanDTO,
  UpcomingReminderResponse,
} from "@/types/api";

export interface DCAPlanCreate {
  index_code: string;
  fund_code?: string | null;
  amount: string;
  frequency: "WEEKLY" | "BIWEEKLY" | "MONTHLY";
  day_of_period: number;
  start_date: string;
  enabled?: boolean;
}

export interface DCAPlanUpdate {
  amount?: string;
  frequency?: "WEEKLY" | "BIWEEKLY" | "MONTHLY";
  day_of_period?: number;
  enabled?: boolean;
  fund_code?: string | null;
}

export function fetchDCAPlans(): Promise<DCAPlanDTO[]> {
  return apiGet<DCAPlanDTO[]>("/dca-plans");
}

export function createDCAPlan(body: DCAPlanCreate): Promise<DCAPlanDTO> {
  return apiPost<DCAPlanDTO>("/dca-plans", body);
}

export function updateDCAPlan(id: number, body: DCAPlanUpdate): Promise<DCAPlanDTO> {
  return apiPut<DCAPlanDTO>(`/dca-plans/${id}`, body);
}

export function deleteDCAPlan(id: number): Promise<void> {
  return apiDelete(`/dca-plans/${id}`);
}

export function fetchExecutions(planId: number): Promise<DCAExecutionDTO[]> {
  return apiGet<DCAExecutionDTO[]>(`/dca-plans/${planId}/executions`);
}

export function fetchUpcoming(within = 7): Promise<UpcomingReminderResponse> {
  return apiGet<UpcomingReminderResponse>(`/dca-reminders/upcoming?within_days=${within}`);
}

export function markDone(execId: number): Promise<DCAExecutionDTO> {
  return apiPost<DCAExecutionDTO>(`/dca-executions/${execId}/mark-done`, {});
}

export function markSkipped(execId: number): Promise<DCAExecutionDTO> {
  return apiPost<DCAExecutionDTO>(`/dca-executions/${execId}/skip`, {});
}

export interface DCAPlanStatsDTO {
  plan_id: number;
  index_code: string;
  index_name: string;
  done_count: number;
  skipped_count: number;
  pending_count: number;
  done_total_amount: string;
  skipped_total_amount: string;
  base_total_if_no_adjustment: string;
  skip_ratio: string;
  average_multiplier: string;
}

export interface DCAStatsResponse {
  plans: DCAPlanStatsDTO[];
  total_done_amount: string;
  total_skipped_amount: string;
}

export function fetchDCAStats(): Promise<DCAStatsResponse> {
  return apiGet<DCAStatsResponse>("/dca-plans/stats");
}
