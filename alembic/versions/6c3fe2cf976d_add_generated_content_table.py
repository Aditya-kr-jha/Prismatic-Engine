"""add_generated_content_table

Revision ID: 6c3fe2cf976d
Revises: a26543338aa2
Create Date: 2026-01-12 18:13:26.140187

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c3fe2cf976d'
down_revision: Union[str, Sequence[str], None] = 'a26543338aa2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
