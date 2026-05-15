/**
 * Decide which driver in each team should render with a dashed line.
 *
 * In a 2-driver team the "lowest-placed" teammate is the one with the
 * smaller final cumulative-points value. Single-driver teams are never
 * dashed. Ties break by giving the second-listed driver the dashed line
 * (deterministic so the chart doesn't flicker across renders).
 */

export interface TeammatePoint {
  code: string;
  team: string;
  cumulative: number[];
}

export function pickDashedTeammates(drivers: TeammatePoint[]): Set<string> {
  const byTeam = new Map<string, TeammatePoint[]>();
  for (const d of drivers) {
    if (!d.team) continue;
    const list = byTeam.get(d.team) ?? [];
    list.push(d);
    byTeam.set(d.team, list);
  }

  const dashed = new Set<string>();
  for (const list of byTeam.values()) {
    if (list.length < 2) continue;
    // reduce without seed uses list[0] as accumulator — safe since length >= 2.
    const lowest = list.reduce((lo, next) =>
      lastValue(next.cumulative) <= lastValue(lo.cumulative) ? next : lo,
    );
    dashed.add(lowest.code);
  }
  return dashed;
}

function lastValue(arr: number[]): number {
  return arr.at(-1) ?? 0;
}
