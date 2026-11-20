"""default 1099 boxes for existing companies

Revision ID: e0a5d1df30a6
Revises: 143488f52c74
Create Date: 2026-11-20 11:06:25.350180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0a5d1df30a6'
down_revision: Union[str, Sequence[str], None] = '143488f52c74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default accounts that get a 1099 box (same as app/seed/default_accounts.py).
DEFAULT_BOXES = [
    ("6900", "Contractors", "NEC_1"),
    ("6500", "Rent & Lease", "MISC_1"),
]


def upgrade() -> None:
    """Give companies created before 1099 support the same default 1099 boxes as new ones."""
    for code, name, box in DEFAULT_BOXES:
        op.execute(
            sa.text(
                "UPDATE accounts SET box_1099 = :box "
                "WHERE code = :code AND name = :name AND box_1099 IS NULL"
            ).bindparams(box=box, code=code, name=name)
        )


def downgrade() -> None:
    """Nothing to undo: the column itself is removed by the previous migration's downgrade."""
    pass
