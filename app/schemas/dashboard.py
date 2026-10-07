"""
Pydantic response schemas for public pulse dashboar data
"""

from pydantic import BaseModel






class DashboardSummaryResponse(BaseModel):
    """
    Aggregating complaint statistics ofr the dashboard


    <total_complaints, by_status, by_category, by_pincode>

    period_days:
    None -> all time data
    7 means complaints created in last 7 days
    """

    period_days: int | None

    total_complaints: int

    by_status: dict[str, int]

    by_category: dict[str, int]

    by_pincode: dict[str, int]


# {
#   "by_status": {
#     "draft": 5,
#     "sent": 12
#   }
# }


class CityComparisonCityResponse(BaseModel):
    """
    City metadata used by dashboard comparisons.
    """

    city_id: int

    city_name: str

    population: int


class CityCategoryComplaintRateResponse(BaseModel):
    """
    Category-level complaint rate for one city.
    """

    city_id: int

    city_name: str

    population: int

    category: str

    complaint_count: int

    complaints_per_10000: float


class CityComplaintComparisonResponse(BaseModel):
    """
    Comparison of selected cities using complaints per 10,000 people.
    """

    period_days: int | None

    cities: list[CityComparisonCityResponse]

    category_rates: list[CityCategoryComplaintRateResponse]
