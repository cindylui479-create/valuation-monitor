import { apiGet } from "./client";
export function fetchTushareUsage() {
    return apiGet("/tushare-usage");
}
