import { friendlyMessage } from "@/lib/validation-messages";
// Used by the admin screens, which run in the browser. Requests go through the /api rewrite,
// so the login cookies travel with them automatically.

export class AdminApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(`Admin API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

type Options = Omit<RequestInit, "body" | "headers"> & {
  json?: unknown; // sent as JSON
  body?: BodyInit; // or raw data such as FormData (file uploads)
  headers?: Record<string, string>;
};

// Login, refresh and logout never trigger an automatic refresh.
const NO_REFRESH = ["/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/logout"];

// Refresh tokens rotate: a second refresh with the old token would fail and log the user out.
// So when several requests hit a 401 at once, they all wait for one shared refresh.
let refreshing: Promise<boolean> | null = null;

function refreshSession(): Promise<boolean> {
  refreshing ??= fetch("/api/v1/auth/refresh", { method: "POST" })
    .then((res) => res.ok)
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function adminFetch<T = void>(path: string, options: Options = {}): Promise<T> {
  const { json, body, headers, ...rest } = options;

  const send = () =>
    fetch(path, {
      ...rest,
      headers: {
        ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
        ...headers,
      },
      body: json !== undefined ? JSON.stringify(json) : body,
    });

  let res = await send();
  if (res.status === 401 && !NO_REFRESH.includes(path) && (await refreshSession())) {
    res = await send(); // one retry with the fresh cookies
  }
  if (!res.ok) throw new AdminApiError(res.status, await res.json().catch(() => null));
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// Turns a failed admin request into messages for the screen.
// FastAPI's validation errors look like {"detail": [{"loc": ["body", "email"], "msg": "..."}]}.
export function describeError(error: unknown): {
  fields: Record<string, string>;
  general: string | null;
} {
  const fields: Record<string, string> = {};
  if (!(error instanceof AdminApiError)) {
    return { fields, general: "We couldn't reach the server. Please try again." };
  }

  const detail = (error.body as { detail?: unknown } | null)?.detail;
  if (Array.isArray(detail)) {
    for (const item of detail) {
      const loc = (item as { loc?: unknown[] }).loc;
      const msg = (item as { msg?: unknown }).msg;
      const field = Array.isArray(loc) ? loc[loc.length - 1] : undefined;
      if (typeof field === "string" && typeof msg === "string") fields[field] = friendlyMessage(msg);
    }
    if (Object.keys(fields).length > 0) return { fields, general: null };
  }

  if (error.status === 401) {
    return { fields, general: "Your session has ended. Reload the page to sign in again." };
  }
  if (error.status === 403) return { fields, general: "You don't have permission to do that." };
  if (typeof detail === "string") return { fields, general: detail };
  return { fields, general: "Something went wrong. Please try again." };
}