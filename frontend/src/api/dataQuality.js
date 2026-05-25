import { apiGet, apiPatch } from "./client";
export function fetchDataQualitySummary(includeAcknowledged = false) {
    const q = includeAcknowledged ? "?include_acknowledged=true" : "";
    return apiGet(`/data-quality/summary${q}`);
}
export function fetchDataQualityDetail(code) {
    return apiGet(`/data-quality/${encodeURIComponent(code)}`);
}
export function setAnomalyAck(anomalyId, acknowledged, note) {
    return apiPatch(`/data-quality/anomaly/${anomalyId}`, {
        acknowledged,
        note: note ?? null,
    });
}
