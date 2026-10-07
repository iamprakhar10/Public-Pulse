"""add city population

Revision ID: 9a12f4d7c3b8
Revises: 63a7b3e22fc1
Create Date: 2026-10-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a12f4d7c3b8'
down_revision: Union[str, Sequence[str], None] = '63a7b3e22fc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CITY_POPULATIONS = {
    "Jabalpur": 1267564,
    "Indore": 1994397,
    "Jaipur": 3046163,
    "Kota": 1001694,
    "Lucknow": 2817105,
}


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'cities',
        sa.Column(
            'population',
            sa.Integer(),
            nullable=True,
        ),
    )

    cities = sa.table(
        'cities',
        sa.column('name', sa.String),
        sa.column('population', sa.Integer),
    )

    for city_name, population in CITY_POPULATIONS.items():
        op.execute(
            cities.update()
            .where(cities.c.name == city_name)
            .values(population=population)
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column(
        'cities',
        'population',
    )
