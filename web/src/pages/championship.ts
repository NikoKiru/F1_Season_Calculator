/** Championship detail page: season-progression line chart from SSR JSON. */

import { lineChart } from "../components/charts/factories";
import { $, readJsonScript } from "../lib/dom";
import { pickDashedTeammates } from "../lib/teammates";

interface PagePayload {
  rounds: string[];
  drivers: { code: string; team: string; color: string; cumulative: number[] }[];
}

async function render(): Promise<void> {
  const canvas = $<HTMLCanvasElement>("[data-chart='season-progression']");
  const data = readJsonScript<PagePayload>("page-data");
  if (!canvas || !data) return;
  const [first] = data.drivers;
  if (!first) return;

  const labels = data.rounds.length ? data.rounds : first.cumulative.map((_, i) => `R${i + 1}`);
  const dashed = pickDashedTeammates(data.drivers);
  const series = data.drivers.map((d) => ({
    label: d.code,
    color: d.color,
    data: d.cumulative,
    dashed: dashed.has(d.code),
  }));

  await lineChart(canvas, labels, series, "Round", "Cumulative points");
}

render();
