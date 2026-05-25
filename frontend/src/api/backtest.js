import { apiPost } from "./client";
export function runBacktest(body) {
    return apiPost("/backtest/run", body);
}
export function exportCsvUrl(indexCode, window = "10y") {
    return `/api/v1/exports/index/${encodeURIComponent(indexCode)}.csv?window=${window}`;
}
