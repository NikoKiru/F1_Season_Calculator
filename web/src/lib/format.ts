/** Small formatters used across pages — keeps UI strings consistent. */

const ORDINAL_RULES = new Intl.PluralRules("en", { type: "ordinal" });
const ORDINAL_SUFFIXES: Record<Intl.LDMLPluralRule, string> = {
  zero: "th",
  one: "st",
  two: "nd",
  few: "rd",
  many: "th",
  other: "th",
};

export function ordinal(n: number): string {
  const suffix = ORDINAL_SUFFIXES[ORDINAL_RULES.select(n)] ?? "th";
  return `${n}${suffix}`;
}

export function formatNumber(n: number): string {
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 10_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toLocaleString("en-US");
}

export function formatPercent(ratio: number, digits = 1): string {
  return `${ratio.toFixed(digits)}%`;
}

export function pluralize(count: number, singular: string, plural?: string): string {
  return count === 1 ? `${count} ${singular}` : `${count} ${plural ?? `${singular}s`}`;
}
