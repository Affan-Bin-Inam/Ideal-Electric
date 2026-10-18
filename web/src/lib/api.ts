import "server-only";

const API_ORIGIN = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

// Carries the HTTP status, so callers can tell "not found" from "broken".
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_ORIGIN}${path}`);
  if (!res.ok) {
    throw new ApiError(res.status, `API request failed: ${path} (${res.status})`);
  }
  return res.json() as Promise<T>;
}