import { apiGet } from "./client";
export function fetchPipelineRuns(days = 30) {
    return apiGet(`/pipeline-runs?days=${days}`);
}
