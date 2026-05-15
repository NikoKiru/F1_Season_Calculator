/**
 * Tiny color utility — used to give two teammates distinguishable slices
 * in a pie chart when they share the same team color.
 */

export function darkenHex(hex: string, amount = 0.35): string {
  const m = hex.replace("#", "");
  if (m.length !== 6) return hex;
  const r = clamp(Math.round(parseInt(m.slice(0, 2), 16) * (1 - amount)));
  const g = clamp(Math.round(parseInt(m.slice(2, 4), 16) * (1 - amount)));
  const b = clamp(Math.round(parseInt(m.slice(4, 6), 16) * (1 - amount)));
  return `#${hex2(r)}${hex2(g)}${hex2(b)}`;
}

function clamp(n: number): number {
  return Math.max(0, Math.min(255, n));
}

function hex2(n: number): string {
  return n.toString(16).padStart(2, "0");
}
