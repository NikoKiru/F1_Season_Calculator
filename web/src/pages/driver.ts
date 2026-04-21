/**
 * Driver detail page: stat tiles are SSR; the position-bar and
 * season-length line charts fetch + render client-side. The state host
 * is separate from the chart wrapper so loading/error panels can render
 * without destroying the <canvas> elements.
 */

import { barChart, lineChart } from "../components/charts/factories";
import { showError, showLoading } from "../components/states";
import { apiGet } from "../lib/api";
import { $, readJsonScript } from "../lib/dom";
import type { DriverStats } from "../lib/types";

interface PagePayload {
  driver_code: string;
  season: number;
  color: string;
}

function stateHost(): HTMLElement | null {
  return $<HTMLElement>("[data-state-host]");
}

function chartsWrapper(): HTMLElement | null {
  return $<HTMLElement>("[data-charts-wrapper]");
}

function showState(panelHtml: (host: HTMLElement) => void): void {
  const host = stateHost();
  const wrapper = chartsWrapper();
  if (!host || !wrapper) return;
  wrapper.setAttribute("hidden", "");
  panelHtml(host);
}

function showCharts(): void {
  const host = stateHost();
  const wrapper = chartsWrapper();
  if (!host || !wrapper) return;
  host.innerHTML = "";
  wrapper.removeAttribute("hidden");
}

async function hydrateCharts(payload: PagePayload): Promise<void> {
  const barCanvas = $<HTMLCanvasElement>("[data-chart='position-distribution']");
  const lineCanvas = $<HTMLCanvasElement>("[data-chart='win-probability-by-length']");
  if (!barCanvas || !lineCanvas) return;

  showState((host) => showLoading(host, "Loading charts…"));

  let stats: DriverStats;
  try {
    stats = await apiGet<DriverStats>(
      `/api/drivers/${encodeURIComponent(payload.driver_code)}/stats`,
      { params: { season: payload.season }, timeoutMs: 8000 },
    );
  } catch (err) {
    showState((host) => showError(host, err, () => hydrateCharts(payload)));
    return;
  }

  showCharts();

  const positions = Object.keys(stats.position_distribution).sort((a, b) => Number(a) - Number(b));
  const positionCounts = positions.map((p) => stats.position_distribution[p] ?? 0);
  await barChart(barCanvas, positions.map((p) => `P${p}`), positionCounts, payload.color, "Count");

  const lengths = Object.keys(stats.win_probability_by_length).sort((a, b) => Number(a) - Number(b));
  const winRates = lengths.map((l) => stats.win_probability_by_length[l] ?? 0);
  await lineChart(
    lineCanvas,
    lengths,
    [{ label: "Win probability %", color: payload.color, data: winRates }],
    "Season length (races)",
    "Win %",
  );
}

const payload = readJsonScript<PagePayload>("page-data");
if (payload) void hydrateCharts(payload);
