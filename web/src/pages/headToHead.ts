/**
 * Head-to-head: two slot pickers + a swap button + a pie chart that fetches
 * when both slots are filled.
 *
 * Layout invariant: the canvas lives inside [data-chart-wrapper] and is
 * NEVER replaced by state panels — state panels render into the sibling
 * [data-state-host] and the wrapper is toggled via `hidden`. This preserves
 * the canvas across re-renders, so consecutive picks don't destroy it.
 */

import { pieChart } from "../components/charts/factories";
import { showError, showLoading } from "../components/states";
import { apiGet } from "../lib/api";
import { $, readJsonScript, require$ } from "../lib/dom";

interface PagePayload {
  season: number;
  drivers: { code: string; name: string; color: string; team: string }[];
}

interface HeadToHeadResponse {
  [driver: string]: number;
}

function getSlot(id: string): HTMLSelectElement {
  return require$<HTMLSelectElement>(`[data-slot='${id}']`);
}

function stateHost(): HTMLElement {
  return require$<HTMLElement>("[data-state-host]");
}

function chartWrapper(): HTMLElement {
  return require$<HTMLElement>("[data-chart-wrapper]");
}

function showState(html: string): void {
  chartWrapper().hidden = true;
  stateHost().innerHTML = html;
}

function showChartSurface(): void {
  stateHost().innerHTML = "";
  chartWrapper().hidden = false;
}

async function refresh(payload: PagePayload): Promise<void> {
  const a = getSlot("a").value;
  const b = getSlot("b").value;

  if (!a || !b) {
    showState(`<div class="state-panel"><p class="state-panel__title">Pick two drivers</p></div>`);
    return;
  }
  if (a === b) {
    showState(`<div class="state-panel" role="alert"><p class="state-panel__title">Choose two different drivers</p></div>`);
    return;
  }

  chartWrapper().hidden = true;
  showLoading(stateHost(), "Comparing…");

  try {
    const res = await apiGet<HeadToHeadResponse>(
      `/api/drivers/head-to-head/${encodeURIComponent(a)}/${encodeURIComponent(b)}`,
      { params: { season: payload.season } },
    );
    const driverA = payload.drivers.find((d) => d.code === a);
    const driverB = payload.drivers.find((d) => d.code === b);
    showChartSurface();
    const canvas = require$<HTMLCanvasElement>("[data-chart='head-to-head']");
    await pieChart(
      canvas,
      [driverA?.name ?? a, driverB?.name ?? b],
      [res[a] ?? 0, res[b] ?? 0],
      [driverA?.color ?? "#e10600", driverB?.color ?? "#1f2937"],
    );
  } catch (err) {
    chartWrapper().hidden = true;
    showError(stateHost(), err, () => refresh(payload));
  }
}

function applyUrlParams(): void {
  const params = new URLSearchParams(window.location.search);
  const a = params.get("a");
  const b = params.get("b");
  if (a) getSlot("a").value = a.toUpperCase();
  if (b) getSlot("b").value = b.toUpperCase();
}

const payload = readJsonScript<PagePayload>("page-data");
if (payload) {
  const a = getSlot("a");
  const b = getSlot("b");
  a.addEventListener("change", () => refresh(payload));
  b.addEventListener("change", () => refresh(payload));

  $<HTMLButtonElement>("[data-swap]")?.addEventListener("click", () => {
    [a.value, b.value] = [b.value, a.value];
    void refresh(payload);
  });

  applyUrlParams();
  void refresh(payload);
}
