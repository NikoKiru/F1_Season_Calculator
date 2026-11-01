/** Constructor-positions page: position picker → constructor list for that slot. */

import { readJsonScript } from "../lib/dom";
import { initPositionsPage, type PositionRow } from "../lib/positionsPage";

interface PagePayload {
  season: number;
  constructor_names: Record<string, string>;   // slug → display name
  constructor_colors: Record<string, string>;  // slug → hex color
}

interface ConstructorRow extends PositionRow {
  constructor: string;  // canonical team name (matches values in constructor_names)
}

function slugFor(name: string, payload: PagePayload): string {
  // The payload's constructor_names map is slug → name; invert to find slug.
  for (const [slug, display] of Object.entries(payload.constructor_names)) {
    if (display === name) return slug;
  }
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

const payload = readJsonScript<PagePayload>("page-data");
if (payload) {
  initPositionsPage<ConstructorRow>({
    endpoint: "/api/constructors/positions",
    season: payload.season,
    emptyMessage: (position) => `No constructor has finished P${position} yet.`,
    card: (row) => {
      const slug = slugFor(row.constructor, payload);
      return {
        name: row.constructor,
        color: payload.constructor_colors[slug] ?? "#666",
        profileHref: `/constructor/${encodeURIComponent(slug)}`,
        profileLabel: "Constructor page",
      };
    },
  });
}
