from pydantic import BaseModel, Field


class RoundPointsEntry(BaseModel):
    round_points: list[int]
    total_points: int


class Championship(BaseModel):
    """A single championship scenario (one subset of rounds)."""
    championship_id: int
    season: int
    num_races: int
    rounds: str = Field(description="Comma-separated round numbers, sorted ascending.")
    standings: str = Field(description="Comma-separated driver codes, sorted by points desc.")
    winner: str | None
    points: str = Field(description="Comma-separated points, aligned with standings.")
    round_names: list[str] | None = None
    driver_points: dict[str, int] | None = None
    driver_names: dict[str, str] | None = None
    round_points_data: dict[str, RoundPointsEntry] | None = None


class ChampionshipSummary(BaseModel):
    """Thin row for per-position tables (driver_position_detail page)."""
    championship_id: int
    num_races: int
    standings: list[str]
    driver_points: int
    margin: int | None
