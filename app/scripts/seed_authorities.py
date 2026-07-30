"""
Inserting dummy authorities record for local defelopment and testing

This script will check already existing authorities before inserting
"""

from sqlalchemy import select

from app.constants.complaint import ComplaintCategory
from app.database.models import Authority, City
from app.database.session import SessionLocal


# One test pincode per supported city for v1 development.
CITY_PINCODES = {
    "Jabalpur": "482005",
    "Indore": "452001",
    "Jaipur": "302001",
    "Kota": "324001",
    "Lucknow": "226001",
}


CATEGORY_DEPARTMENTS = {
    ComplaintCategory.ROAD: "Roads Department",
    ComplaintCategory.WATER: "Water Supply Department",
    ComplaintCategory.ELECTRICITY: "Electricity Department",
    ComplaintCategory.SANITATION: "Sanitation Department",
    ComplaintCategory.POLICE: "Police Department",
    ComplaintCategory.GOVERNMENT_SCHOOL: "Education Department",
    ComplaintCategory.WOMEN_SAFETY: "Women Safety Department",
    ComplaintCategory.CHILD_LABOUR: "Labour Department",
    ComplaintCategory.OVERPRICING: "Consumer Affairs Department",
    ComplaintCategory.OTHER: "Public Grievance Department",
}


def build_dummy_email(
    city_name: str,
    category: ComplaintCategory,
) -> str:
    """
    Create an obviously fake email address for development.

    Example:
        roads.jabalpur@example.com
    """

    city_slug = city_name.lower().replace(" ", "-")
    category_slug = category.value.replace("_", "-")

    return f"{category_slug}.{city_slug}@example.com"


def build_authority_name(
    city_name: str,
    category: ComplaintCategory,
) -> str:
    """
    Return a temporary authority name for dummy development data.
    """

    if category in {
        ComplaintCategory.POLICE,
        ComplaintCategory.WOMEN_SAFETY,
    }:
        return f"{city_name} Police"

    if category == ComplaintCategory.ELECTRICITY:
        return f"{city_name} Electricity Department"

    if category == ComplaintCategory.GOVERNMENT_SCHOOL:
        return f"{city_name} Education Department"

    if category == ComplaintCategory.CHILD_LABOUR:
        return f"{city_name} Labour Department"

    if category == ComplaintCategory.OVERPRICING:
        return f"{city_name} Consumer Affairs Department"

    return f"{city_name} Municipal Corporation"


def seed_authorities() -> None:
    """
    Insert one dummy authority for every category for one pincode
    in each supported city.
    """

    db = SessionLocal()

    inserted_count = 0
    skipped_count = 0

    try:
        for city_name, pincode in CITY_PINCODES.items():

            # Find the canonical City row created by the location seed.
            city_statement = select(City).where(
                City.name == city_name,
                City.is_supported.is_(True),
            )

            city = db.scalar(city_statement)

            if city is None:
                raise ValueError(
                    f"{city_name} was not found in the cities table. "
                    "Run the location seed script first."
                )

            for category, department in CATEGORY_DEPARTMENTS.items():

                # Check whether this city-pincode-category mapping
                # already exists.
                existing_statement = select(Authority).where(
                    Authority.city_id == city.id,
                    Authority.pincode == pincode,
                    Authority.category == category,
                )

                existing_authority = db.scalar(
                    existing_statement
                )

                if existing_authority is not None:
                    skipped_count += 1
                    continue

                authority = Authority(
                    name=build_authority_name(
                        city_name=city_name,
                        category=category,
                    ),
                    department=department,
                    category=category,
                    city_id=city.id,
                    pincode=pincode,
                    email=build_dummy_email(
                        city_name=city_name,
                        category=category,
                    ),
                    is_active=True,
                )

                db.add(authority)
                inserted_count += 1

        db.commit()

        print(
            "Authority seed complete: "
            f"{inserted_count} inserted, "
            f"{skipped_count} already existed."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_authorities()