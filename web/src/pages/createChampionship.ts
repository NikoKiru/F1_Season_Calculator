/**
 * Create-championship page: round toggle grid + Random + Submit.
 * Submit hits /api/championships/search and redirects on success.
 */

import { showError, showLoading } from "../components/states";
import { apiGet } from "../lib/api";
import { $, $$, readJsonScript, require$ } from "../lib/dom";

interface PagePayload {
  season: number;
  total_rounds: number;
}

interface SearchResponse {
  championship_id: number;
  url: string;
}

function selectedRounds(): number[] {
  return $$<HTMLInputElement>("input[name='round']:checked")
    .map((el) => Number(el.value))
    .sort((a, b) => a - b);
}

function randomise(total: number): void {
  const count = Math.max(1, Math.floor(Math.random() * total) + 1);
  const picks = new Set<number>();
  while (picks.size < count) picks.add(Math.floor(Math.random() * total) + 1);
  for (const input of $$<HTMLInputElement>("input[name='round']")) {
    input.checked = picks.has(Number(input.value));
  }
}

async function submit(
  payload: PagePayload,
  feedbackHost: HTMLElement,
  submitBtn: HTMLButtonElement,
): Promise<void> {
  const rounds = selectedRounds();
  if (rounds.length === 0) {
    feedbackHost.innerHTML = `<p class="error-message">Pick at least one round.</p>`;
    return;
  }
  showLoading(feedbackHost, "Searching for championship…");
  submitBtn.disabled = true;
  try {
    const res = await apiGet<SearchResponse>("/api/search/championship", {
      params: { rounds: rounds.join(","), season: payload.season },
      timeoutMs: 15_000,
    });
    window.location.assign(res.url);
  } catch (err) {
    submitBtn.disabled = false;
    showError(feedbackHost, err, () => submit(payload, feedbackHost, submitBtn));
  }
}

function resetForm(feedback: HTMLElement, submitBtn: HTMLButtonElement): void {
  feedback.innerHTML = "";
  feedback.removeAttribute("aria-busy");
  submitBtn.disabled = false;
}

const payload = readJsonScript<PagePayload>("page-data");
if (payload) {
  const submitBtn = require$<HTMLButtonElement>("[data-submit]");
  const feedback = require$<HTMLElement>("[data-feedback]");
  $<HTMLButtonElement>("[data-random]")?.addEventListener("click", () => randomise(payload.total_rounds));
  submitBtn.addEventListener("click", () => submit(payload, feedback, submitBtn));
  // Browsers snapshot the DOM into the back-forward cache at navigation
  // time. Without this, returning to the page (e.g. clicking back from
  // the result) restores the frozen "Searching for championship…" panel
  // with the submit button still disabled. Clear that state on bfcache
  // restore so the form is usable again.
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) resetForm(feedback, submitBtn);
  });
}
