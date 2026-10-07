"""
Dashboard API routes public pulse
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.orm import Session

from app.database.dependencies import (
    get_db
)
from app.database.location_crud import get_supported_cities
from app.schemas.dashboard import (
    CityComplaintComparisonResponse,
    DashboardSummaryResponse,
)
from app.schemas.location import CityResponse
from app.services.dashboard import (
    get_city_category_complaint_rates,
    get_dashboard_summary,
)


















router = APIRouter(
    prefix="/dashboard",
    tags=['Dashboard'],
)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
)
def get_summary(
    days : int | None = Query(
        default=None,
        ge=1,
        le=365,
        description=(
            "Only include complaints created within "
            "the last N days. Omit for all-time data."
        ),
    ),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    """
    Returns aggregated civic complaint statistics

    eg.
    /dashboard/summary
        -> all-time

    /dashboard/summary?days=7
        -> complaints created in the last 7 days
    """

    summary = get_dashboard_summary(
        db=db,
        days=days,
    )

    return DashboardSummaryResponse(
        **summary,
    )


@router.get(
    "/cities",
    response_model=list[CityResponse],
)
def list_dashboard_cities(
    db: Session = Depends(get_db),
) -> list[CityResponse]:
    """
    Returns supported cities that can be selected in dashboard filters.
    """

    return get_supported_cities(
        db,
    )


@router.get(
    "/city-comparison",
    response_model=CityComplaintComparisonResponse,
)
def compare_city_complaint_rates(
    city_id: list[int] = Query(
        min_length=2,
        max_length=2,
        description=(
            "Exactly two different city IDs to compare by "
            "complaints per 10,000 people."
        ),
    ),
    days: int | None = Query(
        default=None,
        ge=1,
        le=365,
        description=(
            "Only include complaints created within "
            "the last N days. Omit for all-time data."
        ),
    ),
    db: Session = Depends(get_db),
) -> CityComplaintComparisonResponse:
    """
    Compare two cities by category using complaint counts normalized
    by population.
    """

    unique_city_ids = list(
        dict.fromkeys(
            city_id,
        )
    )

    if len(unique_city_ids) != 2:
        raise HTTPException(
            status_code=400,
            detail="Please choose two different cities.",
        )

    comparison = get_city_category_complaint_rates(
        db=db,
        city_ids=unique_city_ids,
        days=days,
    )

    if len(comparison["cities"]) != 2:
        raise HTTPException(
            status_code=404,
            detail=(
                "Both cities must be supported and have "
                "population data."
            ),
        )

    return CityComplaintComparisonResponse(
        period_days=days,
        **comparison,
    )
