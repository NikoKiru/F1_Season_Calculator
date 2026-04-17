from pydantic import BaseModel, Field, RootModel

from app.domain.driver import DriverInfo


class AllChampionshipWins(RootModel[dict[str, int]]):
    """Driver code → total championship wins."""


class MinRacesToWin(RootModel[dict[str, int]]):
    """Driver code → smallest num_races at which they ever won."""


class HighestPosition(BaseModel):
    driver: str
    position: int
    max_races: int | None
    max_races_championship_id: int | None
    best_margin: int | None
    best_margin_championship_id: int | None


class PositionCount(BaseModel):
    driver: str
    count: int
    percentage: float


class HeadToHead(RootModel[dict[str, int]]):
    """{driver1_code: d1_wins, driver2_code: d2_wins} — keys preserved in request order."""


class HeadToHeadBreakdown(BaseModel):
    wins: int
    losses: int


class DriverStats(BaseModel):
    driver_code: str
    driver_name: str
    driver_info: DriverInfo
    total_wins: int
    total_championships: int
    win_percentage: float
    highest_position: int
    highest_position_championship_id: int | None
    min_races_to_win: int | None
    position_distribution: dict[int, int]
    win_probability_by_length: dict[int, float]
    seasons_per_length: dict[int, int]
    head_to_head: dict[str, HeadToHeadBreakdown]
    season: int


class WinProbabilityRow(BaseModel):
    driver: str
    total_titles: int
    wins_per_length: list[int]
    percentages: list[float]


class WinProbability(BaseModel):
    season: int
    season_lengths: list[int]
    possible_seasons: list[int]
    drivers_data: list[WinProbabilityRow]
    driver_names: dict[str, str]


class DriverPositionChampionships(BaseModel):
    driver_code: str
    driver_name: str
    position: int
    total_count: int
    page: int
    per_page: int
    total_pages: int
    championships: list
    season: int


class ChampionshipsPage(BaseModel):
    total_results: int
    total_pages: int
    current_page: int
    per_page: int
    season: int
    next_page: str | None
    prev_page: str | None
    results: list = Field(description="Formatted championship dicts (see Championship model).")
