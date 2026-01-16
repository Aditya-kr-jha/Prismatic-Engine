"""add evergreen source youtube enum

Revision ID: 31734632cca0
Revises: 6c3fe2cf976d
Create Date: 2026-01-17 00:39:42.884906

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31734632cca0'
down_revision: Union[str, Sequence[str], None] = '6c3fe2cf976d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
