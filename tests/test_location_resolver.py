"""
Tests for canonical city resolution.
"""

import pytest

from app.database.session import SessionLocal
from app.services.location_resolver import (
    normalize_location_name,
    resolve_city,
)


def test_normalize_location_name() -> None:
    """
    Verify that case, spacing and punctuation are normalized.
    """

    assert (
        normalize_location_name("  JABALPUR  ")
        == "jabalpur"
    )

    assert (
        normalize_location_name("Jabalpur-City")
        == "jabalpur city"
    )


def test_resolve_city_by_canonical_name() -> None:
    """
    Resolve a city using its canonical name.
    """

    db = SessionLocal()

    try:
        city = resolve_city(
            db=db,
            city_name="Jabalpur",
            state_code="MP",
        )

        assert city.name == "Jabalpur"
        assert city.state.code == "MP"

    finally:
        db.close()


def test_resolve_city_by_alias() -> None:
    """
    Resolve common aliases to their canonical city.
    """

    db = SessionLocal()

    try:
        city = resolve_city(
            db=db,
            city_name="JBP",
        )

        assert city.name == "Jabalpur"

    finally:
        db.close()


def test_resolve_city_is_case_insensitive() -> None:
    """
    City resolution should not depend on capitalisation.
    """

    db = SessionLocal()

    try:
        city = resolve_city(
            db=db,
            city_name="  lKo ",
        )

        assert city.name == "Lucknow"

    finally:
        db.close()


def test_resolve_unsupported_city_fails() -> None:
    """
    Unknown cities must not be silently guessed.
    """

    db = SessionLocal()

    try:
        with pytest.raises(
            ValueError,
            match="Could not resolve supported city",
        ):
            resolve_city(
                db=db,
                city_name="Mumbai",
            )

    finally:
        db.close()


def test_alias_and_state_must_agree() -> None:
    """
    An alias must belong to the supplied state.
    """

    db = SessionLocal()

    try:
        with pytest.raises(
            ValueError,
            match=(
                "The city alias does not belong "
                "to the supplied state"
            ),
        ):
            resolve_city(
                db=db,
                city_name="JBP",
                state_code="RJ",
            )

    finally:
        db.close()