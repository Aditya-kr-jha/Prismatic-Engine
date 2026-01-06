"""add phase 4 strategy models v2

Revision ID: 336666b3c17a
Revises: 782eb8162e4b
Create Date: 2026-01-04 20:10:14.583276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '336666b3c17a'
down_revision: Union[str, Sequence[str], None] = '782eb8162e4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
