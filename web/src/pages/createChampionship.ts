/**
 * Create-championship page: round toggle grid + Random + Submit.
 * Submit hits /api/championships/search and redirects on success.
 */

import { showError } from "../components/states";
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

async function submit(payload: PagePayload, feedbackHost: HTMLElement): Promise<void> {
  const rounds = selectedRounds();
  if (rounds.length === 0) {
    feedbackHost.innerHTML = `<p class="error-message">Pick at least one round.</p>`;
    return;
  }
  feedbackHost.innerHTML = "";
  try {
    const res = await apiGet<SearchResponse>("/api/search/championship", {
      params: { rounds: rounds.join(","), season: payload.season },
      timeoutMs: 10_000,
    });
    window.location.assign(res.url);
  } catch (err) {
    showError(feedbackHost, err, () => submit(payload, feedbackHost));
  }
}

const payload = readJsonScript<PagePayload>("page-data");
if (payload) {
  const submitBtn = require$<HTMLButtonElement>("[data-submit]");
  const feedback = require$<HTMLElement>("[data-feedback]");
  $<HTMLButtonElement>("[data-random]")?.addEventListener("click", () => randomise(payload.total_rounds));
  submitBtn.addEventListener("click", () => submit(payload, feedback));
}
