"""
Database queries for states, cities and city aliases.

This module only retrieves database records. Decisions such as
whether a match is ambiguous belong in the location resolver service.

Canonical city:
Jabalpur

Aliases stored by us:
jbp
jabalpur city
jubbulpore
"""

from sqlalchemy import select
from sqlalchemy.orm import  Session

from app.database.models import City, CityAlias, State


def get_state_by_code(
        db:Session,
        state_code:str,
) -> State | None:
    """
    Will return a state using it's short code

    mp and MP will both search for MP
    """

    statement = select(State).where(
        State.code ==state_code.strip().upper(),
    )

    return db.scalar(statement)


def get_cities_by_normalized_name(
        db: Session,
        normalized_name: str,
        state_id: int | None=None,
) -> list[City]:
    """
    Returns supported city matching a canonical normalized name

    A list will be returned as same city name could theoritically
    """

    statement = select(City).where(
        City.normalized_name == normalized_name,
        City.is_supported.is_(True),
    )

    if state_id is not None:
        statement = statement.where(
            City.state_id == state_id,
        )

    result = db.execute(statement)

    return list(result.scalars().all())



def get_city_by_normalized_alias(
        db:Session,
        normalized_alias:str,
) -> City | None:
    """
    Resolving a registered alias to it's canonical supported city
    """
    statement = (
        select(City)
        .join(
            CityAlias,
            CityAlias.city_id == City.id,
        )
        .where(
            CityAlias.normalized_alias == normalized_alias,
            City.is_supported.is_(True),
        )
    )

    return db.scalar(statement)


def get_supported_cities(
        db:Session,
) -> list[City]:
    """
    Returning every currently supported city by public-pulse
    """
    statement =( 
        select(City)
        .where(
            City.is_supported.is_(True),
        )
        .order_by(
            City.name.asc(),
        )
    )

    result = db.execute(statement)

    return list(result.scalars().all())