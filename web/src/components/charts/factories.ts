/**
 * Opinionated Chart.js factories — every chart in the app goes through one of
 * these so defaults (font, grid, tooltip) stay consistent.
 *
 * `lineChart` uses the `labels + data[]` shape (idiomatic Chart.js on a
 * category x-axis). The previous `{x, y}` + `parsing: false` combination
 * silently rendered an empty canvas because unparsed points never got mapped
 * to axis positions.
 */

import type { ChartConfiguration } from "chart.js";
import { makeChart } from "./loader";

export interface LineSeries {
  label: string;
  data: number[];
  color: string;
  /** Render this series with a dashed stroke (e.g. lower-placed teammate). */
  dashed?: boolean;
}

export async function lineChart(
  canvas: HTMLCanvasElement,
  labels: string[],
  series: LineSeries[],
  xLabel = "",
  yLabel = "",
) {
  const config: ChartConfiguration<"line"> = {
    type: "line",
    data: {
      labels,
      datasets: series.map((s) => ({
        label: s.label,
        data: s.data,
        borderColor: s.color,
        backgroundColor: s.color,
        tension: 0.2,
        pointRadius: 3,
        borderDash: s.dashed ? [6, 4] : undefined,
      })),
    },
    options: {
      ...sharedOptions(series.length > 1),
      scales: axes(xLabel, yLabel),
    },
  };
  return makeChart(canvas, config);
}

export async function barChart(
  canvas: HTMLCanvasElement,
  labels: string[],
  values: number[],
  colors: string | string[],
  yLabel = "",
) {
  const config: ChartConfiguration<"bar"> = {
    type: "bar",
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: colors, borderRadius: 6 }],
    },
    options: { ...sharedOptions(false), scales: axes("", yLabel) },
  };
  return makeChart(canvas, config);
}

export async function pieChart(
  canvas: HTMLCanvasElement,
  labels: string[],
  values: number[],
  colors: string[],
) {
  // Slice borders use the page background so adjacent slices are always
  // visually separated, including when teammates share a team color.
  const sliceBorder = getSliceBorder(canvas);
  const config: ChartConfiguration<"pie"> = {
    type: "pie",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderColor: sliceBorder,
        borderWidth: 2,
      }],
    },
    options: sharedOptions(),
  };
  return makeChart(canvas, config);
}

function getSliceBorder(canvas: HTMLCanvasElement): string {
  const v = getComputedStyle(canvas).getPropertyValue("--bg-app").trim();
  return v || "#0b0d10";
}

function sharedOptions(withLegend = true) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 400 },
    plugins: {
      legend: {
        display: withLegend,
        position: "bottom" as const,
        labels: { usePointStyle: true, padding: 16 },
      },
      tooltip: {
        backgroundColor: "rgba(17,24,39,0.95)",
        padding: 10,
        cornerRadius: 6,
      },
    },
  };
}

function axes(xLabel: string, yLabel: string) {
  return {
    x: {
      title: { display: Boolean(xLabel), text: xLabel },
      grid: { display: false },
    },
    y: {
      beginAtZero: true,
      title: { display: Boolean(yLabel), text: yLabel },
      ticks: { precision: 0 },
    },
  };
}
