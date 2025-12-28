"""deleted blog scrappers tables v2

Revision ID: a0f34be1b552
Revises: 7f7562aad66b
Create Date: 2025-12-29 02:47:44.868566

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0f34be1b552'
down_revision: Union[str, Sequence[str], None] = '7f7562aad66b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
