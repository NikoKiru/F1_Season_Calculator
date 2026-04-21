/** Driver-positions page: position picker buttons → driver list for that slot. */

import { showError, showLoading } from "../components/states";
import { apiGet } from "../lib/api";
import { $, $$, readJsonScript, require$ } from "../lib/dom";

interface PagePayload {
  season: number;
  driver_names: Record<string, string>;
}

interface PositionRow {
  driver: string;
  count: number;
  percentage: number;
}

let activeController: AbortController | null = null;

async function fetchPosition(payload: PagePayload, position: number): Promise<void> {
  const host = require$<HTMLElement>("[data-position-results]");

  activeController?.abort();
  const controller = new AbortController();
  activeController = controller;

  showLoading(host, `Loading P${position}…`);

  try {
    const rows = await apiGet<PositionRow[]>("/api/drivers/positions", {
      params: { position, season: payload.season },
      signal: controller.signal,
    });
    if (controller.signal.aborted) return;
    host.innerHTML = renderRows(payload, position, rows);
  } catch (err) {
    if (controller.signal.aborted) return;
    showError(host, err, () => fetchPosition(payload, position));
  }
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

function renderRows(payload: PagePayload, position: number, rows: PositionRow[]): string {
  if (rows.length === 0) {
    return `<div class="state-panel"><p class="state-panel__title">Nobody has finished P${position} yet.</p></div>`;
  }
  return `
    <h3 class="section__title">P${position} finishers</h3>
    <ul class="grid grid--drivers">
      ${rows
        .map((r) => {
          const name = escapeHtml(payload.driver_names[r.driver] ?? r.driver);
          return `
        <li class="card">
          <p class="card__title">${name}</p>
          <p class="card__subtitle">${r.count.toLocaleString()} championships (${r.percentage.toFixed(1)}%)</p>
        </li>`;
        })
        .join("")}
    </ul>`;
}

const payload = readJsonScript<PagePayload>("page-data");
if (payload) {
  for (const btn of $$<HTMLButtonElement>("[data-position]")) {
    btn.addEventListener("click", () => {
      for (const other of $$<HTMLButtonElement>("[data-position]")) other.setAttribute("aria-pressed", "false");
      btn.setAttribute("aria-pressed", "true");
      void fetchPosition(payload, Number(btn.dataset.position));
    });
  }
}
