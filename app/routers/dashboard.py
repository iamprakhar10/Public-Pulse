"""
Dashboard API routes public pulse
"""

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.orm import Session

from app.database.dependencies import (
    get_db
)
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard import get_dashboard_summary


















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