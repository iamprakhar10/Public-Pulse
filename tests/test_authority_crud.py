from app.constants.complaint import ComplaintCategory
from app.database.authority_crud import (
    get_authority_for_complaint,
)
from app.database.session import SessionLocal
from app.services.location_resolver import resolve_city


def test_get_authority_for_valid_complaint() -> None:
    """
    A valid city, pincode and category should return the matching
    active authority.
    """

    db = SessionLocal()

    try:
        city = resolve_city(
            db=db,
            city_name="Jabalpur",
        )

        authority = get_authority_for_complaint(
            db=db,
            city_id=city.id,
            pincode="482005",
            category=ComplaintCategory.ROAD,
        )

        assert authority is not None
        assert authority.city_id == city.id
        assert authority.pincode == "482005"
        assert authority.category == ComplaintCategory.ROAD
        assert authority.email == "road.jabalpur@example.com"
        assert authority.is_active is True

    finally:
        db.close()


def test_get_authority_returns_none_for_wrong_city_pincode() -> None:
    """
    A pincode belonging to another city must not match a Jabalpur
    authority.
    """

    db = SessionLocal()

    try:
        city = resolve_city(
            db=db,
            city_name="Jabalpur",
        )

        authority = get_authority_for_complaint(
            db=db,
            city_id=city.id,
            pincode="302001",  # Jaipur dummy pincode
            category=ComplaintCategory.ROAD,
        )

        assert authority is None

    finally:
        db.close()


def test_get_authority_for_other_category() -> None:
    """
    A valid OTHER-category authority should also be returned.
    """

    db = SessionLocal()

    try:
        city = resolve_city(
            db=db,
            city_name="Jabalpur",
        )

        authority = get_authority_for_complaint(
            db=db,
            city_id=city.id,
            pincode="482005",
            category=ComplaintCategory.OTHER,
        )

        assert authority is not None
        assert authority.city_id == city.id
        assert authority.pincode == "482005"
        assert authority.category == ComplaintCategory.OTHER
        assert authority.email == "other.jabalpur@example.com"

    finally:
        db.close()