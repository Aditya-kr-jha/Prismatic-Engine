"""remove lifecycle metadata from content atom

Revision ID: a26543338aa2
Revises: 336666b3c17a
Create Date: 2026-01-06 14:24:55.134186

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a26543338aa2'
down_revision: Union[str, Sequence[str], None] = '336666b3c17a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
