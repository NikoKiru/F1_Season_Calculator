/**
 * Loading / error / empty state renderers — every async pane routes through
 * these three helpers so the UX is identical across pages.
 */

import { ApiRequestError, ApiTimeoutError } from "../lib/api";

type RetryFn = () => void;

export function showLoading(host: HTMLElement, label = "Loading…"): void {
  host.setAttribute("aria-busy", "true");
  host.innerHTML = `
    <div class="state-panel" role="status" aria-live="polite">
      <div class="spinner" aria-hidden="true"></div>
      <p class="state-panel__title">${escape(label)}</p>
    </div>
  `;
}

export function showEmpty(host: HTMLElement, title: string, description?: string): void {
  host.removeAttribute("aria-busy");
  host.innerHTML = `
    <div class="state-panel" role="status">
      <p class="state-panel__title">${escape(title)}</p>
      ${description ? `<p>${escape(description)}</p>` : ""}
    </div>
  `;
}

export function showError(host: HTMLElement, err: unknown, onRetry?: RetryFn): void {
  host.removeAttribute("aria-busy");
  const { title, body } = describe(err);

  host.innerHTML = `
    <div class="state-panel" role="alert">
      <p class="state-panel__title">${escape(title)}</p>
      <p>${escape(body)}</p>
      ${onRetry ? `<button type="button" class="btn btn--primary" data-action="retry">Try again</button>` : ""}
    </div>
  `;
  if (onRetry) {
    host.querySelector<HTMLButtonElement>('[data-action="retry"]')?.addEventListener(
      "click",
      onRetry,
      { once: true },
    );
  }
}

function describe(err: unknown): { title: string; body: string } {
  if (err instanceof ApiTimeoutError) {
    return {
      title: "Taking longer than expected",
      body: "The server didn't respond in time. Retry when you're ready.",
    };
  }
  if (err instanceof ApiRequestError) {
    return {
      title: err.status === 404 ? "Not found" : "Something went wrong",
      body: err.payload?.message ?? err.message,
    };
  }
  if (err instanceof Error) return { title: "Something went wrong", body: err.message };
  return { title: "Something went wrong", body: "Please try again." };
}

function escape(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}
