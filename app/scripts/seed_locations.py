"""
Seed supported states, cities and aliases

Running it repeatedly shouldn't create duplicate records
i.e. The script is idempotent
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import City, CityAlias, State
from app.database.session import SessionLocal
from app.services.location_resolver import normalize_location_name



STATES = [
    {
        "name": "Madhya Pradesh",
        "code": "MP",
    },
    {
        "name": "Rajasthan",
        "code": "RJ",
    },
    {
        "name": "Uttar Pradesh",
        "code": "UP",
    },
]


CITIES = [
    {
        "name": "Jabalpur",
        "state_code": "MP",
        "aliases": [
            "Jabalpur City",
            "Jubbulpore",
            "JBP",
        ],
    },
    {
        "name": "Indore",
        "state_code": "MP",
        "aliases": [
            "Indore City",
        ],
    },
    {
        "name": "Jaipur",
        "state_code": "RJ",
        "aliases": [
            "Jaipur City",
        ],
    },
    {
        "name": "Kota",
        "state_code": "RJ",
        "aliases": [
            "Kota City",
        ],
    },
    {
        "name": "Lucknow",
        "state_code": "UP",
        "aliases": [
            "Lucknow City",
            "LKO",
        ],
    },
]




def get_or_create_state(
        db:Session,
        name:str,
        code:str,
) -> State:
    """
    Creatinging an state/ if already present returning the state
    """
    normalized_code = code.strip().upper()

    statement = select(State).where(
        State.code == normalized_code,
    )
    state = db.scalar(statement)

    if state is not None:
        return state

    state = State(
        name=name.strip(),
        code=normalized_code,
    )

    db.add(state)
    db.flush()

    return state


def get_or_create_city(
        db:Session,
        name:str,
        state:State,
) -> City:
    """
    Creatinging an city/ if already present returning the city
    """
    normalized_name = normalize_location_name(
        name
    )
    statement = select(City).where(
        City.normalized_name == normalized_name,
        City.state_id == state.id,
    )

    city = db.scalar(statement)

    if city is not None:
        return city

    city = City(
        name=name.strip(),
        normalized_name=normalized_name,
        state_id=state.id,
        is_supported=True,
    )

    db.add(city)
    db.flush()

    return city



def create_alias_if_missing(
        db:Session,
        city: City,
        alias:str,
) -> None:
    """
    We will; create an alias if normalized alias is not present in database
    jbP -> jbp (created)
    jBp -> jbp (Won't be created as both have same normalized alias)
    """

    normalized_alias = normalize_location_name(
        alias
    )
    statement = select(CityAlias).where(
        CityAlias.normalized_alias == normalized_alias,
    )

    existing_alias = db.scalar(statement)

    if existing_alias is not None:
        if existing_alias.city_id != city.id:
            raise ValueError(
                f"Alias '{alias}' is already assigned to ANOTHER city"
            )
        
        return 
    db.add(
        CityAlias(
            alias=alias.strip(),
            normalized_alias=normalized_alias,
            city_id=city.id,
        )
    )



def seed_locations(
        db: Session
)-> None:
    """
    Insert all supported states, cities and aliases.
    """

    states_by_code: dict[str, State] = {}

    for state_data in STATES:
        state = get_or_create_state(
            db=db,
            name=state_data["name"],
            code=state_data["code"],
        )

        states_by_code[state.code] = state

    for city_data in CITIES:
        state = states_by_code[
            city_data["state_code"]
        ]

        city = get_or_create_city(
            db=db,
            name=city_data["name"],
            state=state,
        )

        for alias in city_data["aliases"]:
            create_alias_if_missing(
                db=db,
                city=city,
                alias=alias,
            )

    db.commit()



def main() -> None:
    """
    Open a database session and seed location data.
    """

    db = SessionLocal()

    try:
        seed_locations(db)

        print(
            "States, cities and aliases seeded successfully."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()