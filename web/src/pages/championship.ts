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
  const [first] = data.drivers;
  if (!first) return;

  const labels = data.rounds.length ? data.rounds : first.cumulative.map((_, i) => `R${i + 1}`);
  const series = data.drivers.map((d) => ({
    label: d.code,
    color: d.color,
    data: d.cumulative,
  }));

  await lineChart(canvas, labels, series, "Round", "Cumulative points");
}

render();
