/**
 * Chart.js loader — dynamic-imported so only pages that render charts pull it.
 * Chart.js is registered once; re-entrant calls reuse the same module.
 */

import type { Chart as ChartType, ChartConfiguration } from "chart.js";

let chartModule: Promise<typeof import("chart.js")> | null = null;

async function loadChart() {
  if (!chartModule) {
    chartModule = import("chart.js").then((mod) => {
      mod.Chart.register(...mod.registerables);
      return mod;
    });
  }
  return chartModule;
}

export async function makeChart(
  canvas: HTMLCanvasElement,
  config: ChartConfiguration,
): Promise<ChartType> {
  const { Chart } = await loadChart();
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
  return new Chart(canvas, config);
}
