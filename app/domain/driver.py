from datetime import date, datetime

from pydantic import BaseModel, Field


class CareerStats(BaseModel):
    """Cumulative F1 career totals — refreshed from Jolpica/Ergast."""
    wins: int | None = None
    podiums: int | None = None
    poles: int | None = None
    championships: int | None = None
    starts: int | None = None
    updated_at: datetime | None = None


class DriverInfo(BaseModel):
    """Single driver record as returned to the frontend."""
    name: str
    team: str
    number: int
    flag: str
    color: str = Field(description="Hex color string inherited from the driver's team.")
    nationality: str | None = None
    birthdate: date | None = None
    debut_year: int | None = None
    jolpica_id: str | None = None
    career: CareerStats | None = None


class Driver(BaseModel):
    """Driver with its 3-letter code."""
    code: str = Field(min_length=3, max_length=3, description="Uppercase 3-letter driver code.")
    info: DriverInfo
