"""
Model may extract uncertain city names such as:
    "JBP"
    "  jabalpur city "
    "JABALPUR"

This service converts that text into one trusted City database record.
"""

import re

from sqlalchemy.orm import Session

from app.database.location_crud import(
    get_cities_by_normalized_name,
    get_city_by_normalized_alias,
    get_state_by_code,
)
from app.database.models import City




def normalize_location_name(
        value: str,
) -> str:
    
    """
    Normalize a city or alias before database lookup.

    Operations:
    1. Remove leading and trailing spaces.
    2. Convert text to case-insensitive lowercase form.
    3. Replace punctuation with spaces.
    4. Collapse repeated spaces.

    Examples:
        "  JABALPUR  " -> "jabalpur"
        "Jabalpur-City" -> "jabalpur city"
        "J.B.P." -> "j b p"
    """
    # This code is copied from chatgpt
    cleaned_value = value.strip().casefold()

    # Replace punctuation and special symbols with spaces.
    cleaned_value = re.sub(
        r"[^\w\s]",
        " ",
        cleaned_value,
    )

    # Replace multiple spaces with one space.
    return " ".join(
        cleaned_value.split()
    )


def resolve_city(
        db: Session,
        city_name: str, #llm output
        state_code: str | None = None,
) -> City:
    """
    Resolving free text(str) city input to one canonical City object

    1. Validating the optional state code
    2. searching the canonical city name
    3. searching resgistered city aliases.
    4. Raising an error instead of silently guessing, as we don't 
       want to email the wrong authorities
    """

    if not city_name.strip():
        raise ValueError(
            "City name is empty"
        )

    normalized_city_name = normalize_location_name(
        city_name
    )

    state_id: int | None = None

    if state_code is not None:
        state = get_state_by_code(
            db=db,
            state_code=state_code,
        )

        if state is None:
            raise ValueError(
                f"Unsupported state code: {state_code}"
            )

        state_id = state.id

    # First we try the city's canonical name
    matching_cities = get_cities_by_normalized_name(
        db=db,
        normalized_name=normalized_city_name,
        state_id=state_id,
    )

    if len(matching_cities) == 1:
        return matching_cities[0]

    if len(matching_cities) > 1:
        raise ValueError(
            'The city name is ambiguious. Please provide the state'
        )

    # If canonical name didn't matched, try an aliaws
    alias_city = get_city_by_normalized_alias(
        db=db,
        normalized_alias=normalized_city_name,
    )

    if alias_city is not None:
        # When user supplied a state, confirm that the alias
        # belongs to a city in that state 

        if (
            state_id is not None
            and alias_city.state_id != state_id
        ):
            raise ValueError(
            "The city alias does not belong to the supplied state"
            )
        return alias_city
    
    # We won't guess an unknown spelling
    raise ValueError(
        f"Could not resolve supported city: {city_name}"
    )
