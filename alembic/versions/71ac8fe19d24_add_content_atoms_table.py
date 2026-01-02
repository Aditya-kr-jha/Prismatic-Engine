"""add content_atoms table

Revision ID: 71ac8fe19d24
Revises: a0f34be1b552
Create Date: 2026-01-02 18:00:44.975445

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71ac8fe19d24'
down_revision: Union[str, Sequence[str], None] = 'a0f34be1b552'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
