import { apiGet } from "./client";
export function fetchIndicesList() {
    return apiGet("/indices");
}
