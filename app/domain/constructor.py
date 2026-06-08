from datetime import datetime

from pydantic import BaseModel


class PalmaresStats(BaseModel):
    """Cumulative team palmarès — refreshed from Jolpica/Ergast."""
    championships: int | None = None
    wins: int | None = None
    podiums: int | None = None
    first_race_year: int | None = None
    updated_at: datetime | None = None


class ConstructorInfo(BaseModel):
    """Hand-curated team identity + palmarès for the detail-page hero.

    Color stays in SeasonData.teams; this model carries only the hero-info
    fields that the existing teams dict doesn't have.
    """
    country: str | None = None
    founded: int | None = None
    principal: str | None = None
    power_unit: str | None = None
    chassis: str | None = None
    jolpica_id: str | None = None
    palmares: PalmaresStats | None = None
