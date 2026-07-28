"""add approved complaint status

Revision ID: 7495663443e7
Revises: b0ec14ec667d
Create Date: 2026-07-29 02:41:14.533369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7495663443e7'
down_revision: Union[str, Sequence[str], None] = 'b0ec14ec667d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Replace the old complaint-status check constraint with one
    that also allows the approved state.
    """

    op.drop_constraint(
        "complaint_status",
        "complaints",
        type_="check",
    )

    op.create_check_constraint(
        "complaint_status",
        "complaints",
        (
            "status IN ("
            "'draft', "
            "'awaiting_approval', "
            "'approved', "
            "'sent', "
            "'unresolved', "
            "'partially_resolved', "
            "'resolved'"
            ")"
        ),
    )


def downgrade() -> None:
    """
    Restore the previous constraint without the approved state.

    Downgrade will fail if any complaint still has status='approved',
    which is appropriate because that value would no longer be valid.
    """

    op.drop_constraint(
        "complaint_status",
        "complaints",
        type_="check",
    )

    op.create_check_constraint(
        "complaint_status",
        "complaints",
        (
            "status IN ("
            "'draft', "
            "'awaiting_approval', "
            "'sent', "
            "'unresolved', "
            "'partially_resolved', "
            "'resolved'"
            ")"
        ),
    )
