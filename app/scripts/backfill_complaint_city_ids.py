"""
Populate Complaint.city_id using the existing Complaint.city string.

This script is safe to rerun:
complaints that already have city_id are skipped.
"""


from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Complaint
from app.database.session import SessionLocal
from app.services.location_resolver import resolve_city


def backfill_complaint_city_ids(
        db: Session,
) -> tuple[int, int]:
    """
    Resolving existing complaint city strings and save city_id

    Returns a tuple
    (# successfully updated complaints, # complaints that couldn't be resolved)
    """

    statement = select(Complaint).where(
        Complaint.city_id.is_(None),
        Complaint.city.is_not(None),
    )

    complaints = list(
        db.execute(statement).scalars().all()
    )

    updated_count, unresolved_count = 0,0

    for complaint in complaints:
        try:
            city = resolve_city(
                db=db,
                city_name=complaint.city,
            )
        except ValueError:
            unresolved_count += 1
            print(
                f"Could not resolve complaint {complaint.id}: "
                f"{complaint.city!r}"
            )

            continue

        complaint.city_id = city.id
        updated_count += 1

    db.commit()

    return updated_count, unresolved_count 



def main() -> None:
    """
    Open a database session and run the city-ID backfill.
    """

    db = SessionLocal()

    try:
        updated_count, unresolved_count = (
            backfill_complaint_city_ids(db)
        )

        print(
            f"Updated complaints: {updated_count}"
        )

        print(
            f"Unresolved complaints: {unresolved_count}"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()