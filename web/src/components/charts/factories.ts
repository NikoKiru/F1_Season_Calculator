/**
 * Opinionated Chart.js factories — every chart in the app goes through one of
 * these so defaults (type, grid, tooltip, motion) stay consistent.
 *
 * Theme colors are resolved from the live CSS tokens via a probe element
 * (custom properties hold `light-dark()` functions, which only resolve when
 * applied to a real property), and re-applied in place when the header
 * toggle fires `f1sc:themechange` — no reload, no stale charts.
 *
 * `lineChart` uses the `labels + data[]` shape (idiomatic Chart.js on a
 * category x-axis). The previous `{x, y}` + `parsing: false` combination
 * silently rendered an empty canvas because unparsed points never got mapped
 * to axis positions.
 */

import type { Chart as ChartType, ChartConfiguration, ScriptableContext } from "chart.js";
import { makeChart } from "./loader";

export interface LineSeries {
  label: string;
  data: number[];
  color: string;
  /** Render this series with a dashed stroke (e.g. lower-placed teammate). */
  dashed?: boolean;
}

/* ── Theme resolution ─────────────────────────────────────────────── */

interface ChartTheme {
  ink: string;
  muted: string;
  grid: string;
  surface: string;
  fontSans: string;
  fontMono: string;
}

/** Resolve a token to a concrete color by applying it to a real property. */
function resolveColor(probe: HTMLElement, cssVar: string): string {
  probe.style.color = `var(${cssVar})`;
  return getComputedStyle(probe).color;
}

function withAlpha(color: string, alpha: number): string {
  const m = color.match(/rgba?\(([^)]+)\)/);
  if (!m) return color;
  const [r, g, b] = m[1]!.split(",").map((p) => p.trim());
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function chartTheme(): ChartTheme {
  const probe = document.createElement("span");
  probe.style.display = "none";
  document.body.appendChild(probe);
  const ink = resolveColor(probe, "--fg-default");
  const muted = resolveColor(probe, "--fg-muted");
  const surface = resolveColor(probe, "--bg-surface");
  probe.remove();

  const root = getComputedStyle(document.documentElement);
  return {
    ink,
    muted,
    grid: withAlpha(ink, 0.08),
    surface,
    fontSans: root.getPropertyValue("--ff-sans").trim() || "sans-serif",
    fontMono: root.getPropertyValue("--ff-mono").trim() || "monospace",
  };
}

function reducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/* ── Shared options ───────────────────────────────────────────────── */

function sharedOptions(t: ChartTheme, withLegend = true) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: reducedMotion() ? (false as const) : { duration: 650, easing: "easeOutQuart" as const },
    plugins: {
      legend: {
        display: withLegend,
        position: "bottom" as const,
        labels: {
          usePointStyle: true,
          pointStyleWidth: 9,
          boxHeight: 7,
          padding: 16,
          color: t.muted,
          font: { family: t.fontSans, size: 12, weight: 500 as const },
        },
      },
      /* Tooltips are carbon in both themes — they belong to the same layer
       * as the header, so they never need theme re-resolution. */
      tooltip: {
        backgroundColor: "rgba(11, 14, 20, 0.94)",
        titleColor: "#f2f5fa",
        bodyColor: "#c9d2df",
        borderColor: "rgba(255, 255, 255, 0.12)",
        borderWidth: 1,
        padding: 12,
        cornerRadius: 10,
        boxPadding: 6,
        usePointStyle: true,
        titleFont: { family: t.fontSans, size: 12, weight: 600 as const },
        bodyFont: { family: t.fontMono, size: 12 },
      },
    },
  };
}

function axes(t: ChartTheme, xLabel: string, yLabel: string) {
  const title = (text: string) => ({
    display: Boolean(text),
    text,
    color: t.muted,
    font: { family: t.fontSans, size: 12, weight: 500 as const },
  });
  return {
    x: {
      title: title(xLabel),
      grid: { display: false },
      border: { color: t.grid },
      ticks: { color: t.muted, font: { family: t.fontSans, size: 11 } },
    },
    y: {
      beginAtZero: true,
      title: title(yLabel),
      grid: { color: t.grid, drawTicks: false },
      border: { display: false },
      ticks: {
        color: t.muted,
        padding: 8,
        precision: 0,
        font: { family: t.fontMono, size: 11 },
      },
    },
  };
}

/* ── Live theme sync ──────────────────────────────────────────────── */

const live = new Set<ChartType>();

function register(chart: ChartType): ChartType {
  live.add(chart);
  return chart;
}

function applyTheme(chart: ChartType, t: ChartTheme): void {
  const legendLabels = chart.options.plugins?.legend?.labels;
  if (legendLabels) legendLabels.color = t.muted;

  const scales = chart.options.scales as unknown as ReturnType<typeof axes> | undefined;
  if (scales?.x) {
    scales.x.ticks.color = t.muted;
    scales.x.title.color = t.muted;
    scales.x.border.color = t.grid;
  }
  if (scales?.y) {
    scales.y.ticks.color = t.muted;
    scales.y.title.color = t.muted;
    scales.y.grid.color = t.grid;
  }

  // Surface-colored separators (doughnut slice borders, line hover rings).
  const type = (chart.config as { type?: string }).type;
  for (const ds of chart.data.datasets) {
    if (type === "doughnut" && "borderColor" in ds) ds.borderColor = t.surface;
    if (type === "line" && "pointBorderColor" in ds) ds.pointBorderColor = t.surface;
  }
  chart.update("none");
}

window.addEventListener("f1sc:themechange", () => {
  const t = chartTheme();
  for (const chart of live) {
    if (!chart.canvas || !chart.canvas.isConnected) {
      live.delete(chart);
      continue;
    }
    applyTheme(chart, t);
  }
});

/* ── Factories ────────────────────────────────────────────────────── */

/** Soft vertical fade under a single-series line. */
function verticalFade(color: string) {
  return (context: ScriptableContext<"line">) => {
    const { ctx, chartArea } = context.chart;
    if (!chartArea) return "transparent";
    const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    gradient.addColorStop(0, withAlpha(hexToRgb(color), 0.2));
    gradient.addColorStop(1, withAlpha(hexToRgb(color), 0));
    return gradient;
  };
}

function hexToRgb(color: string): string {
  const m = color.match(/^#?([0-9a-f]{6})$/i);
  if (!m) return color.startsWith("rgb") ? color : "rgb(128, 128, 128)";
  const n = parseInt(m[1]!, 16);
  return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`;
}

export async function lineChart(
  canvas: HTMLCanvasElement,
  labels: string[],
  series: LineSeries[],
  xLabel = "",
  yLabel = "",
) {
  const t = chartTheme();
  const solo = series.length === 1;
  const config: ChartConfiguration<"line"> = {
    type: "line",
    data: {
      labels,
      datasets: series.map((s) => ({
        label: s.label,
        data: s.data,
        borderColor: s.color,
        backgroundColor: solo ? verticalFade(s.color) : s.color,
        fill: solo ? "origin" : false,
        borderWidth: 2,
        borderCapStyle: "round",
        borderJoinStyle: "round",
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBorderWidth: 2,
        pointBorderColor: t.surface,
        pointBackgroundColor: s.color,
        pointHitRadius: 16,
        borderDash: s.dashed ? [6, 4] : undefined,
      })),
    },
    options: {
      ...sharedOptions(t, series.length > 1),
      interaction: { mode: "index", intersect: false },
      scales: axes(t, xLabel, yLabel),
    },
  };
  return register(await makeChart(canvas, config));
}

export async function barChart(
  canvas: HTMLCanvasElement,
  labels: string[],
  values: number[],
  colors: string | string[],
  yLabel = "",
) {
  const t = chartTheme();
  const config: ChartConfiguration<"bar"> = {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: colors,
          borderRadius: { topLeft: 4, topRight: 4 },
          borderSkipped: "bottom" as const,
          maxBarThickness: 44,
        },
      ],
    },
    options: { ...sharedOptions(t, false), scales: axes(t, "", yLabel) },
  };
  return register(await makeChart(canvas, config));
}

export async function pieChart(
  canvas: HTMLCanvasElement,
  labels: string[],
  values: number[],
  colors: string[],
) {
  const t = chartTheme();
  const total = values.reduce((sum, v) => sum + v, 0);
  const config: ChartConfiguration<"doughnut"> = {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: colors,
          // Surface-colored borders keep adjacent slices separated, even
          // when teammates share a team color.
          borderColor: t.surface,
          borderWidth: 2,
          hoverOffset: 8,
        },
      ],
    },
    options: {
      ...sharedOptions(t),
      cutout: "58%",
      plugins: {
        ...sharedOptions(t).plugins,
        tooltip: {
          ...sharedOptions(t).plugins.tooltip,
          callbacks: {
            label: (item) => {
              const value = Number(item.raw) || 0;
              const pct = total > 0 ? ((value / total) * 100).toFixed(1) : "0.0";
              return ` ${item.label}: ${value.toLocaleString()} (${pct}%)`;
            },
          },
        },
      },
    },
  };
  return register(await makeChart(canvas, config));
}
