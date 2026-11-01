/** Driver-positions page: position picker buttons → driver list for that slot. */

import { readJsonScript } from "../lib/dom";
import { initPositionsPage, type PositionRow } from "../lib/positionsPage";

interface PagePayload {
  season: number;
  driver_names: Record<string, string>;
  driver_colors: Record<string, string>;
}

interface DriverRow extends PositionRow {
  driver: string;
}

const payload = readJsonScript<PagePayload>("page-data");
if (payload) {
  initPositionsPage<DriverRow>({
    endpoint: "/api/drivers/positions",
    season: payload.season,
    emptyMessage: (position) => `Nobody has finished P${position} yet.`,
    card: (row) => ({
      name: payload.driver_names[row.driver] ?? row.driver,
      color: payload.driver_colors[row.driver] ?? "#666",
      profileHref: `/driver/${encodeURIComponent(row.driver)}`,
      profileLabel: "Driver page",
    }),
  });
}
