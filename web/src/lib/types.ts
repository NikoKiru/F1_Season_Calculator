/** Shapes returned by the FastAPI layer. Kept in sync with app/domain/*. */

export interface DriverInfo {
  code: string;
  name: string;
  team: string;
  color: string;
}

export interface SeasonMeta {
  year: number;
  drivers: DriverInfo[];
  rounds: { round: number; name: string }[];
}

export interface ChampionshipSummary {
  championship_id: number;
  num_races: number;
  rounds: string;
  winner: string | null;
  points: string;
  standings: string;
}

export interface Championship extends ChampionshipSummary {
  round_names?: string[];
  driver_points?: Record<string, number>;
  driver_names?: Record<string, string>;
}

export interface DriverStats {
  driver_code: string;
  driver_name: string;
  driver_info: DriverInfo;
  total_wins: number;
  total_championships: number;
  win_percentage: number;
  highest_position: number;
  highest_position_championship_id: number | null;
  min_races_to_win: number | null;
  position_distribution: Record<string, number>;
  win_probability_by_length: Record<string, number>;
  seasons_per_length: Record<string, number>;
  head_to_head: Record<string, { wins: number; losses: number }>;
  season: number;
}

export interface ConstructorStats {
  constructor_name: string;
  slug: string;
  color: string;
  total_wins: number;
  total_championships: number;
  win_percentage: number;
  highest_position: number;
  highest_position_championship_id: number | null;
  min_races_to_win: number | null;
  position_distribution: Record<string, number>;
  win_probability_by_length: Record<string, number>;
  seasons_per_length: Record<string, number>;
  head_to_head: Record<string, { wins: number; losses: number }>;
  season: number;
}

export interface WinProbabilityRow {
  driver_code: string;
  probabilities: Record<string, number>;
}

export interface ApiError {
  code: string;
  message: string;
  [key: string]: unknown;
}
