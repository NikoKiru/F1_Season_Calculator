/**
 * What Driver Positions and Constructor Positions share: a position picker, a
 * card for each finisher, and the chosen position kept in the URL (?p=N).
 */

import { showError, showLoading } from "../components/states";
import { apiGet } from "./api";
import { $, $$, escapeHtml, require$ } from "./dom";

export interface PositionRow {
  count: number;
  percentage: number;
}

interface PositionCard {
  name: string;
  color: string;
  profileHref: string;  // its scenarios live at {profileHref}/position/{n}
  profileLabel: string;
}

interface PositionsPage<Row extends PositionRow> {
  endpoint: string;
  season: number;
  emptyMessage: (position: number) => string;
  card: (row: Row) => PositionCard;
}

function renderCard(card: PositionCard, row: PositionRow, position: number): string {
  const scenariosHref = `${card.profileHref}/position/${position}`;
  return `
        <li class="card card--interactive"
            style="--team-color: ${card.color}"
            onclick="window.location.assign('${scenariosHref}')">
          <div class="card__accent" aria-hidden="true"></div>
          <p class="card__title"><a href="${scenariosHref}">${escapeHtml(card.name)}</a></p>
          <p class="card__subtitle">${row.count.toLocaleString()} championships (${row.percentage.toFixed(1)}%)</p>
          <p class="card__meta">
            <a class="card__stat-link" href="${card.profileHref}" onclick="event.stopPropagation()">${card.profileLabel} →</a>
          </p>
        </li>`;
}

function renderRows<Row extends PositionRow>(
  page: PositionsPage<Row>,
  position: number,
  rows: Row[],
): string {
  if (rows.length === 0) {
    return `<div class="state-panel"><p class="state-panel__title">${page.emptyMessage(position)}</p></div>`;
  }
  return `
    <h3 class="section__title">P${position} finishers</h3>
    <ul class="grid grid--drivers">
      ${rows.map((row) => renderCard(page.card(row), row, position)).join("")}
    </ul>`;
}

export function initPositionsPage<Row extends PositionRow>(page: PositionsPage<Row>): void {
  let activeController: AbortController | null = null;

  async function fetchPosition(position: number): Promise<void> {
    const host = require$<HTMLElement>("[data-position-results]");

    activeController?.abort();
    const controller = new AbortController();
    activeController = controller;

    showLoading(host, `Loading P${position}…`);

    try {
      const rows = await apiGet<Row[]>(page.endpoint, {
        params: { position, season: page.season },
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      host.innerHTML = renderRows(page, position, rows);
    } catch (err) {
      if (controller.signal.aborted) return;
      showError(host, err, () => fetchPosition(position));
    }
  }

  function activate(btn: HTMLButtonElement): void {
    for (const other of $$<HTMLButtonElement>("[data-position]")) other.setAttribute("aria-pressed", "false");
    btn.setAttribute("aria-pressed", "true");
    void fetchPosition(Number(btn.dataset.position));
  }

  for (const btn of $$<HTMLButtonElement>("[data-position]")) {
    btn.addEventListener("click", () => {
      // Keep the chosen position in the URL so results are shareable links.
      const params = new URLSearchParams(window.location.search);
      params.set("p", btn.dataset.position ?? "");
      window.history.replaceState(null, "", `?${params}`);
      activate(btn);
    });
  }

  // Deep link: ?p=7 selects P7 on load.
  const requested = new URLSearchParams(window.location.search).get("p");
  if (requested) {
    const btn = $<HTMLButtonElement>(`[data-position='${CSS.escape(requested)}']`);
    if (btn) activate(btn);
  }
}
