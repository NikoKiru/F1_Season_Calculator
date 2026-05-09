/** Home page: cumulative points line chart for top-5 drivers. */

import { lineChart } from "../components/charts/factories";
import { $, readJsonScript } from "../lib/dom";
import { pickDashedTeammates } from "../lib/teammates";

interface PagePayload {
  drivers: { code: string; team: string; color: string; cumulative: number[] }[];
  rounds: string[];
}

async function render(): Promise<void> {
  const canvas = $<HTMLCanvasElement>("[data-chart='cumulative-points']");
  const data = readJsonScript<PagePayload>("page-data");
  if (!canvas || !data) return;
  const [first] = data.drivers;
  if (!first) return;

  const labels = data.rounds.length ? data.rounds : first.cumulative.map((_, i) => `R${i + 1}`);
  // Compute over the full driver list so a top-5 driver still gets a dashed
  // line if their teammate (also top-5) finished higher.
  const dashed = pickDashedTeammates(data.drivers);
  const series = data.drivers.slice(0, 5).map((d) => ({
    label: d.code,
    color: d.color,
    data: d.cumulative,
    dashed: dashed.has(d.code),
  }));

  await lineChart(canvas, labels, series, "Round", "Cumulative points");
}

render();
