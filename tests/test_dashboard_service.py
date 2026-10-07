from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.constants.complaint import ComplaintCategory, ComplaintStatus
from app.database.base import Base
from app.database.models import City, Complaint, State, User
from app.services.dashboard import get_city_category_complaint_rates


def make_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        engine,
    )

    testing_session = sessionmaker(
        bind=engine,
    )

    return testing_session()


def create_city(
        db: Session,
        *,
        name: str,
        population: int,
) -> City:
    state = db.query(
        State,
    ).filter(
        State.code == "TS",
    ).one_or_none()

    if state is None:
        state = State(
            name="Test State",
            code="TS",
        )
        db.add(state)
        db.flush()

    city = City(
        name=name,
        normalized_name=name.lower(),
        state_id=state.id,
        population=population,
        is_supported=True,
    )

    db.add(city)
    db.flush()

    return city


def create_user(
        db: Session,
) -> User:
    user = User(
        name="Dashboard Test User",
        email="dashboard-service@example.com",
        phone="9000000000",
        hashed_password="hashed-password",
    )

    db.add(user)
    db.flush()

    return user


def create_complaint(
        db: Session,
        *,
        user: User,
        city: City,
        category: ComplaintCategory,
        created_at: datetime,
) -> None:
    db.add(
        Complaint(
            user_id=user.id,
            city_id=city.id,
            city=city.name,
            category=category,
            status=ComplaintStatus.DRAFT,
            created_at=created_at,
        )
    )


def test_get_city_category_complaint_rates_normalizes_per_10000_people() -> None:
    db = make_session()

    try:
        first_city = create_city(
            db,
            name="Alpha",
            population=10000,
        )
        second_city = create_city(
            db,
            name="Beta",
            population=20000,
        )
        user = create_user(
            db,
        )
        now = datetime.now(
            timezone.utc,
        )

        create_complaint(
            db,
            user=user,
            city=first_city,
            category=ComplaintCategory.ROAD,
            created_at=now,
        )
        create_complaint(
            db,
            user=user,
            city=first_city,
            category=ComplaintCategory.ROAD,
            created_at=now,
        )
        create_complaint(
            db,
            user=user,
            city=second_city,
            category=ComplaintCategory.WATER,
            created_at=now,
        )

        db.commit()

        comparison = get_city_category_complaint_rates(
            db,
            city_ids=[
                first_city.id,
                second_city.id,
            ],
            days=None,
        )

        rates_by_city_and_category = {
            (
                rate["city_name"],
                rate["category"],
            ): rate
            for rate in comparison["category_rates"]
        }

        alpha_road = rates_by_city_and_category[
            (
                "Alpha",
                "road",
            )
        ]
        beta_water = rates_by_city_and_category[
            (
                "Beta",
                "water",
            )
        ]
        beta_road = rates_by_city_and_category[
            (
                "Beta",
                "road",
            )
        ]

        assert alpha_road["complaint_count"] == 2
        assert alpha_road["complaints_per_10000"] == 2.0
        assert beta_water["complaint_count"] == 1
        assert beta_water["complaints_per_10000"] == 0.5
        assert beta_road["complaint_count"] == 0
        assert beta_road["complaints_per_10000"] == 0.0

    finally:
        db.close()


def test_get_city_category_complaint_rates_applies_period_filter() -> None:
    db = make_session()

    try:
        city = create_city(
            db,
            name="Gamma",
            population=10000,
        )
        other_city = create_city(
            db,
            name="Delta",
            population=10000,
        )
        user = create_user(
            db,
        )
        now = datetime.now(
            timezone.utc,
        )

        create_complaint(
            db,
            user=user,
            city=city,
            category=ComplaintCategory.ROAD,
            created_at=now,
        )
        create_complaint(
            db,
            user=user,
            city=city,
            category=ComplaintCategory.ROAD,
            created_at=now - timedelta(days=45),
        )

        db.commit()

        comparison = get_city_category_complaint_rates(
            db,
            city_ids=[
                city.id,
                other_city.id,
            ],
            days=30,
        )

        rates_by_city_and_category = {
            (
                rate["city_name"],
                rate["category"],
            ): rate
            for rate in comparison["category_rates"]
        }

        gamma_road = rates_by_city_and_category[
            (
                "Gamma",
                "road",
            )
        ]
        delta_road = rates_by_city_and_category[
            (
                "Delta",
                "road",
            )
        ]

        assert gamma_road["complaint_count"] == 1
        assert gamma_road["complaints_per_10000"] == 1.0
        assert delta_road["complaint_count"] == 0
        assert delta_road["complaints_per_10000"] == 0.0

    finally:
        db.close()
