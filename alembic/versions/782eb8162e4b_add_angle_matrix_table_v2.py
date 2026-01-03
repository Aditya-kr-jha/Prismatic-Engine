"""add angle_matrix table v2

Revision ID: 782eb8162e4b
Revises: 2a2327906424
Create Date: 2026-01-03 17:19:19.235428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '782eb8162e4b'
down_revision: Union[str, Sequence[str], None] = '2a2327906424'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
