/**
 * Driver detail page: stat tiles are SSR; the position-bar and
 * season-length line charts fetch + render client-side so the detail view
 * can still deep-link without blocking on JS.
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

async function hydrateCharts(payload: PagePayload): Promise<void> {
  const barCanvas = $<HTMLCanvasElement>("[data-chart='position-distribution']");
  const lineCanvas = $<HTMLCanvasElement>("[data-chart='win-probability-by-length']");
  const host = $<HTMLElement>("[data-charts-host]");
  if (!barCanvas || !lineCanvas || !host) return;

  showLoading(host, "Loading charts…");

  let stats: DriverStats;
  try {
    stats = await apiGet<DriverStats>(
      `/api/drivers/${encodeURIComponent(payload.driver_code)}/stats`,
      { params: { season: payload.season }, timeoutMs: 8000 },
    );
  } catch (err) {
    showError(host, err, () => hydrateCharts(payload));
    return;
  }

  host.innerHTML = ""; // clear loading panel; charts render into their canvases

  const positions = Object.keys(stats.position_distribution).sort((a, b) => Number(a) - Number(b));
  const positionCounts = positions.map((p) => stats.position_distribution[p] ?? 0);
  await barChart(barCanvas, positions.map((p) => `P${p}`), positionCounts, payload.color, "Count");

  const lengths = Object.keys(stats.win_probability_by_length).sort((a, b) => Number(a) - Number(b));
  const winRates = lengths.map((l) => stats.win_probability_by_length[l] ?? 0);
  await lineChart(
    lineCanvas,
    [
      {
        label: "Win probability %",
        color: payload.color,
        data: lengths.map((l, i) => ({ x: l, y: winRates[i] ?? 0 })),
      },
    ],
    "Season length (races)",
    "Win %",
  );
}

const payload = readJsonScript<PagePayload>("page-data");
if (payload) void hydrateCharts(payload);
