"""
Dashboard aggregation service

This module contains db queries used to built
public pulse complaint statistics

Time filtering is based on Complaint.created_at
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.complaint import ComplaintCategory
from app.database.models import City, Complaint


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


def get_city_category_complaint_rates(
        db: Session,
        *,
        city_ids: list[int],
        days: int | None,
) -> dict:
    """
    Return category-level complaint rates per 10,000 people
    for selected supported cities.
    """

    cutoff = get_dashboard_cutoff(days)

    city_statement = (
        select(
            City.id,
            City.name,
            City.population,
        )
        .where(
            City.id.in_(city_ids),
            City.is_supported.is_(True),
            City.population.is_not(None),
            City.population > 0,
        )
        .order_by(
            City.name.asc(),
        )
    )

    city_rows = db.execute(
        city_statement
    ).all()

    cities = [
        {
            "city_id": city_id,
            "city_name": city_name,
            "population": population,
        }
        for city_id, city_name, population in city_rows
    ]

    complaint_statement = (
        select(
            Complaint.city_id,
            Complaint.category,
            func.count(Complaint.id),
        )
        .where(
            Complaint.city_id.in_(
                [
                    city["city_id"]
                    for city in cities
                ]
            ),
            Complaint.category.is_not(None),
        )
        .group_by(
            Complaint.city_id,
            Complaint.category,
        )
    )

    if cutoff is not None:
        complaint_statement = complaint_statement.where(
            Complaint.created_at >= cutoff,
        )

    complaint_rows = db.execute(
        complaint_statement,
    ).all()

    counts_by_city_and_category = {
        (
            city_id,
            category.value,
        ): complaint_count
        for city_id, category, complaint_count in complaint_rows
    }

    category_rates = []

    for city in cities:
        for category in ComplaintCategory:
            complaint_count = counts_by_city_and_category.get(
                (
                    city["city_id"],
                    category.value,
                ),
                0,
            )

            category_rates.append(
                {
                    **city,
                    "category": category.value,
                    "complaint_count": complaint_count,
                    "complaints_per_10000": round(
                        (
                            complaint_count
                            / city["population"]
                        )
                        * 10000,
                        2,
                    ),
                }
            )

    return {
        "cities": cities,
        "category_rates": category_rates,
    }
