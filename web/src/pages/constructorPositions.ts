/** Constructor-positions page: position picker → constructor list for that slot. */

import { showError, showLoading } from "../components/states";
import { apiGet } from "../lib/api";
import { $$, readJsonScript, require$ } from "../lib/dom";

interface PagePayload {
  season: number;
  constructor_names: Record<string, string>;   // slug → display name
  constructor_colors: Record<string, string>;  // slug → hex color
}

interface PositionRow {
  constructor: string;  // canonical team name (matches values in constructor_names)
  count: number;
  percentage: number;
}

let activeController: AbortController | null = null;

function slugFor(name: string, payload: PagePayload): string {
  // The payload's constructor_names map is slug → name; invert to find slug.
  for (const [slug, display] of Object.entries(payload.constructor_names)) {
    if (display === name) return slug;
  }
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

async function fetchPosition(payload: PagePayload, position: number): Promise<void> {
  const host = require$<HTMLElement>("[data-position-results]");

  activeController?.abort();
  const controller = new AbortController();
  activeController = controller;

  showLoading(host, `Loading P${position}…`);

  try {
    const rows = await apiGet<PositionRow[]>("/api/constructors/positions", {
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
    return `<div class="state-panel"><p class="state-panel__title">No constructor has finished P${position} yet.</p></div>`;
  }
  return `
    <h3 class="section__title">P${position} finishers</h3>
    <ul class="grid grid--drivers">
      ${rows
        .map((r) => {
          const name = escapeHtml(r.constructor);
          const slug = slugFor(r.constructor, payload);
          const color = payload.constructor_colors[slug] ?? "#666";
          const href = `/constructor/${encodeURIComponent(slug)}`;
          return `
        <li class="card card--interactive"
            style="--team-color: ${color}"
            onclick="window.location.assign('${href}')">
          <div class="card__accent" aria-hidden="true"></div>
          <p class="card__title"><a href="${href}">${name}</a></p>
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
