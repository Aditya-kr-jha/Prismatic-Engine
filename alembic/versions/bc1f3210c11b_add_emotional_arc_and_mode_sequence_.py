"""add_emotional_arc_and_mode_sequence_columns

Revision ID: bc1f3210c11b
Revises: 31734632cca0
Create Date: 2026-01-18 19:54:41.752966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'bc1f3210c11b'
down_revision: Union[str, Sequence[str], None] = '31734632cca0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add emotional_arc and mode_sequence JSONB columns."""
    op.add_column(
        'generated_content',
        sa.Column(
            'emotional_arc',
            JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        )
    )
    op.add_column(
        'generated_content',
        sa.Column(
            'mode_sequence',
            JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        )
    )


def downgrade() -> None:
    """Remove emotional_arc and mode_sequence columns."""
    op.drop_column('generated_content', 'mode_sequence')
    op.drop_column('generated_content', 'emotional_arc')
