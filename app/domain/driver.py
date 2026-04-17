from pydantic import BaseModel, Field


class DriverInfo(BaseModel):
    """Single driver record as returned to the frontend."""
    name: str
    team: str
    number: int
    flag: str
    color: str = Field(description="Hex color string inherited from the driver's team.")


class Driver(BaseModel):
    """Driver with its 3-letter code."""
    code: str = Field(min_length=3, max_length=3, description="Uppercase 3-letter driver code.")
    info: DriverInfo
