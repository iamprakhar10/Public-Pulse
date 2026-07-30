from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Authority, ComplaintCategory


def get_authority_for_complaint(
    db:Session,
    city_id : int,
    pincode: str,
    category: ComplaintCategory,
) -> Authority|None:
    """
    Finding the active authority who should be sent the email/complaint
    
    Based on city_id+pincode+category

    We have put unique constraint for same city, pincode and category 
    while making tables
    """

    statement = select(Authority).where(
        Authority.city_id == city_id,
        Authority.pincode == pincode,
        Authority.category == category,
        Authority.is_active.is_(True),
    )

    return db.scalar(statement)


def authority_exists_for_location(
        db:Session,
        city_id: int,
        pincode: str,
        category: ComplaintCategory,
) -> bool:
    """
    Checking whether public pulse supports given combination of
    city, pincode, complaint category.
    """

    authority = get_authority_for_complaint(
        db=db,
        city_id=city_id,
        pincode=pincode,
        category=category,
    )

    return authority is not None
