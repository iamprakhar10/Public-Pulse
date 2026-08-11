"""
Dashboard aggregation service

This module contains db queries used to built
public pulse complaint statistics

Time filtering is based on Complaint.created_at
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Complaint


def get_dashboard_cutoff(
        days: int | None,
) -> datetime | None:
    """
    Converts number of days into a UTC cutoff datetime
    """

    if days is None:
        return None

    return (
        datetime.now(timezone.utc)
        - timedelta(days=days)
    )



def get_total_complaints(
        db: Session,
        *,
        cutoff: datetime | None,
) -> int:
    """
    Counts complaint in that time period
    """
    statement = select(
        func.count(Complaint.id)
    )

    if cutoff is not None:
        statement = statement.where(
            Complaint.created_at >= cutoff
        )
    result = db.scalar(
        statement
    )

    return result or 0



def get_complaint_counts_by_status(
        db: Session,
        *,
        cutoff: datetime | None,
) -> dict[str, int] :
    """
    Counts complaints grouped by their current status

    Cutoff feature is also implemented here
    """

    statement = select(
        Complaint.status,
        func.count(Complaint.id),
    )

    if cutoff is not None:
        statement = statement.where(
            Complaint.created_at >= cutoff
        )

    statement = statement.group_by(
        Complaint.status
    )

    rows = db.execute(
        statement
    ).all()

    return {
        status.value: count 
        for status, count in rows
    }


def get_complaint_counts_by_category(
        db: Session,
        *,
        cutoff: datetime | None,
) -> dict[str, int]:
    """
    Count complaints grouped by category.

    Complaints without a category are excluded.
    """

    statement = (
        select(
            Complaint.category,
            func.count(Complaint.id),
        )
        .where(
            Complaint.category.is_not(None)
        )
    )

    if cutoff is not None:
        statement = statement.where(
            Complaint.created_at >= cutoff
        )

    statement = statement.group_by(
        Complaint.category
    )

    rows = db.execute(
        statement
    ).all()

    return {
        category.value: count
        for category, count in rows
    }


def get_complaint_counts_by_pincode(
        db: Session,
        *,
        cutoff: datetime | None,
) -> dict[str, int]:
    """
    Count complaints grouped by pincode.

    Complaints without a pincode are excluded.
    """

    statement = (
        select(
            Complaint.pincode,
            func.count(Complaint.id),
        )
        .where(
            Complaint.pincode.is_not(None)
        )
    )

    if cutoff is not None:
        statement = statement.where(
            Complaint.created_at >= cutoff
        )

    statement = statement.group_by(
        Complaint.pincode
    )

    rows = db.execute(
        statement
    ).all()

    return {
        pincode: count
        for pincode, count in rows
    }



def get_dashboard_summary(
        db: Session,
        *,
        days: int | None,
) -> dict:
    """
    Helps building the complete dashboard summary

    Same cutoff will be reused for all aggregation 
    """

    cutoff = get_dashboard_cutoff(days)

    return {
        "period_days": days,

        "total_complaints": get_total_complaints(
            db,
            cutoff=cutoff,
        ),

        "by_status": get_complaint_counts_by_status(
            db,
            cutoff=cutoff,
        ),

        "by_category": get_complaint_counts_by_category(
            db,
            cutoff=cutoff,
        ),

        "by_pincode": get_complaint_counts_by_pincode(
            db,
            cutoff=cutoff,
        ),
    }