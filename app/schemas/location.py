"""
Pydantic schemas for state and city data.

These schemas control how location objects are returned through
FastAPI and used in tests.
"""

from pydantic import BaseModel, ConfigDict


class StateResponse(BaseModel):
    """
    MC=CD
    Public representation of a state database object.
    """

    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class CityResponse(BaseModel):
    """
    MC=CD
    Public representation of a city database object.
    """

    id: int
    name: str
    normalized_name: str
    state_id: int
    is_supported: bool

    model_config = ConfigDict(from_attributes=True)


class CityResolutionResponse(BaseModel):
    """
    Result returned after free-text city input is resolved
    to a canonical city record.
    """

    city_id: int
    city_name: str
    state_id: int
    state_name: str
    state_code: str

