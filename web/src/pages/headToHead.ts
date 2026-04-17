/**
 * Head-to-head: two slot pickers + a swap button + a pie chart that fetches
 * when both slots are filled.
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

async function refresh(payload: PagePayload): Promise<void> {
  const host = require$<HTMLElement>("[data-chart-host]");
  const canvas = require$<HTMLCanvasElement>("[data-chart='head-to-head']");
  const a = getSlot("a").value;
  const b = getSlot("b").value;

  if (!a || !b) {
    host.innerHTML = `<div class="state-panel"><p class="state-panel__title">Pick two drivers</p></div>`;
    return;
  }
  if (a === b) {
    host.innerHTML = `<div class="state-panel" role="alert"><p class="state-panel__title">Choose two different drivers</p></div>`;
    return;
  }

  showLoading(host, "Comparing…");
  try {
    const res = await apiGet<HeadToHeadResponse>(
      `/api/drivers/head-to-head/${encodeURIComponent(a)}/${encodeURIComponent(b)}`,
      { params: { season: payload.season } },
    );
    host.innerHTML = "";
    host.appendChild(canvas);
    const driverA = payload.drivers.find((d) => d.code === a);
    const driverB = payload.drivers.find((d) => d.code === b);
    await pieChart(
      canvas,
      [driverA?.name ?? a, driverB?.name ?? b],
      [res[a] ?? 0, res[b] ?? 0],
      [driverA?.color ?? "#e10600", driverB?.color ?? "#1f2937"],
    );
  } catch (err) {
    showError(host, err, () => refresh(payload));
  }
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
}
