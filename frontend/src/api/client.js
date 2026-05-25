const BASE = "/api/v1";
async function handle(res) {
    if (!res.ok) {
        const body = (await res.json().catch(() => null));
        const msg = body?.error?.message ?? `HTTP ${res.status}`;
        throw new Error(msg);
    }
    // 204 No Content
    if (res.status === 204)
        return undefined;
    return (await res.json());
}
export async function apiGet(path) {
    return handle(await fetch(`${BASE}${path}`, { headers: { Accept: "application/json" } }));
}
export async function apiPost(path, body) {
    return handle(await fetch(`${BASE}${path}`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(body),
    }));
}
export async function apiPut(path, body) {
    return handle(await fetch(`${BASE}${path}`, {
        method: "PUT",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(body),
    }));
}
export async function apiDelete(path) {
    return handle(await fetch(`${BASE}${path}`, { method: "DELETE" }));
}
export async function apiPatch(path, body) {
    return handle(await fetch(`${BASE}${path}`, {
        method: "PATCH",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(body),
    }));
}
export async function apiRequest(method, path, body) {
    const init = {
        method,
        headers: { Accept: "application/json", "Content-Type": "application/json" },
    };
    if (body !== undefined)
        init.body = JSON.stringify(body);
    return handle(await fetch(`${BASE}${path}`, init));
}
