/** Home page: cumulative points line chart for top-5 drivers. */

import { lineChart } from "../components/charts/factories";
import { $, readJsonScript } from "../lib/dom";

interface PagePayload {
  drivers: { code: string; color: string; cumulative: number[] }[];
  rounds: string[];
}

async function render(): Promise<void> {
  const canvas = $<HTMLCanvasElement>("[data-chart='cumulative-points']");
  const data = readJsonScript<PagePayload>("page-data");
  if (!canvas || !data) return;

  const series = data.drivers.slice(0, 5).map((d) => ({
    label: d.code,
    color: d.color,
    data: d.cumulative.map((y, i) => ({ x: data.rounds[i] ?? String(i + 1), y })),
  }));

  await lineChart(canvas, series, "Round", "Cumulative points");
}

render();
