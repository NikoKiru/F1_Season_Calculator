/** Championship detail page: season-progression line chart from SSR JSON. */

import { lineChart } from "../components/charts/factories";
import { $, readJsonScript } from "../lib/dom";

interface PagePayload {
  rounds: string[];
  drivers: { code: string; color: string; cumulative: number[] }[];
}

async function render(): Promise<void> {
  const canvas = $<HTMLCanvasElement>("[data-chart='season-progression']");
  const data = readJsonScript<PagePayload>("page-data");
  if (!canvas || !data) return;

  const series = data.drivers.map((d) => ({
    label: d.code,
    color: d.color,
    data: d.cumulative.map((y, i) => ({ x: data.rounds[i] ?? String(i + 1), y })),
  }));

  await lineChart(canvas, series, "Round", "Cumulative points");
}

render();
