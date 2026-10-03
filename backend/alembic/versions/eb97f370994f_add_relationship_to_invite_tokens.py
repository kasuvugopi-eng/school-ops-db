"""add relationship to invite_tokens

Revision ID: eb97f370994f
Revises: 12ad8a1cce83
Create Date: 2026-10-03 07:50:43.523305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb97f370994f'
down_revision: Union[str, None] = '12ad8a1cce83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('invite_tokens', sa.Column('relationship', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('invite_tokens', 'relationship')
