/**
 * Single fetch wrapper: AbortController timeouts, typed errors, consistent
 * JSON body handling. Pages never hit `fetch` directly — they go through here.
 */

import type { ApiError } from "./types";

export class ApiRequestError extends Error {
  readonly status: number;
  readonly payload: ApiError | null;
  constructor(status: number, payload: ApiError | null, message: string) {
    super(message);
    this.status = status;
    this.payload = payload;
    this.name = "ApiRequestError";
  }
}

export class ApiTimeoutError extends Error {
  constructor(public readonly timeoutMs: number) {
    super(`Request timed out after ${timeoutMs}ms`);
    this.name = "ApiTimeoutError";
  }
}

interface RequestOptions {
  signal?: AbortSignal;
  /** Hard timeout — triggers a retry-offer in the UI. */
  timeoutMs?: number;
  /** Extra query parameters merged onto the URL. */
  params?: Record<string, string | number | undefined>;
}

const DEFAULT_TIMEOUT_MS = 15000;

function buildUrl(path: string, params: RequestOptions["params"]): string {
  const url = new URL(path, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined) continue;
      url.searchParams.set(k, String(v));
    }
  }
  return url.pathname + url.search;
}

export async function apiGet<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  // Chain the caller's external signal (for fast-clicking AbortController use)
  if (opts.signal) {
    if (opts.signal.aborted) controller.abort();
    else opts.signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  try {
    const res = await fetch(buildUrl(path, opts.params), {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });

    if (!res.ok) {
      const payload = (await safeJson<{ detail?: ApiError }>(res))?.detail ?? null;
      throw new ApiRequestError(
        res.status,
        payload,
        payload?.message ?? `Request failed with ${res.status}`,
      );
    }
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      if (opts.signal?.aborted) throw err;
      throw new ApiTimeoutError(timeoutMs);
    }
    throw err;
  } finally {
    window.clearTimeout(timer);
  }
}

async function safeJson<T>(res: Response): Promise<T | null> {
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
