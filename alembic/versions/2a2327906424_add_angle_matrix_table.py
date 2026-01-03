"""add angle_matrix table

Revision ID: 2a2327906424
Revises: 71ac8fe19d24
Create Date: 2026-01-03 16:52:33.422984

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a2327906424'
down_revision: Union[str, Sequence[str], None] = '71ac8fe19d24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
