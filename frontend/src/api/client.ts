import type { ApiError } from "@/types/api";

const BASE = "/api/v1";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiError | null;
    const msg = body?.error?.message ?? `HTTP ${res.status}`;
    throw new Error(msg);
  }
  // 204 No Content
  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

export async function apiGet<T>(path: string): Promise<T> {
  return handle(await fetch(`${BASE}${path}`, { headers: { Accept: "application/json" } }));
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return handle(
    await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  return handle(
    await fetch(`${BASE}${path}`, {
      method: "PUT",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function apiDelete<T = void>(path: string): Promise<T> {
  return handle(await fetch(`${BASE}${path}`, { method: "DELETE" }));
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return handle(
    await fetch(`${BASE}${path}`, {
      method: "PATCH",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function apiRequest<T>(
  method: string, path: string, body?: unknown,
): Promise<T> {
  const init: RequestInit = {
    method,
    headers: { Accept: "application/json", "Content-Type": "application/json" },
  };
  if (body !== undefined) init.body = JSON.stringify(body);
  return handle(await fetch(`${BASE}${path}`, init));
}
