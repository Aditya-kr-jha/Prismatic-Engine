"""restart initial tables v2 and fixed index error

Revision ID: 7f7562aad66b
Revises: 8ab78d9504af
Create Date: 2025-12-28 18:25:01.929208

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f7562aad66b'
down_revision: Union[str, Sequence[str], None] = '8ab78d9504af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
