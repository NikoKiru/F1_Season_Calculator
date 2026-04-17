from pydantic import BaseModel, Field

from app.domain.driver import DriverInfo


class SeasonData(BaseModel):
    """All config data for a given F1 season — loaded from data/seasons/{year}.json."""
    season: int
    teams: dict[str, str] = Field(description="Team name → team color hex.")
    drivers: dict[str, DriverInfo] = Field(description="Driver code → info.")
    driver_names: dict[str, str] = Field(description="Driver code → display name.")
    round_names: dict[int, str] = Field(description="Round number → circuit abbreviation.")
