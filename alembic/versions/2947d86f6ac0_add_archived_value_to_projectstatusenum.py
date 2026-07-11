"""add archived value to projectstatusenum

Revision ID: 2947d86f6ac0
Revises: 639723473e43
Create Date: 2026-07-11 02:26:22.110961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2947d86f6ac0'
down_revision: Union[str, None] = '639723473e43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE projectstatusenum ADD VALUE IF NOT EXISTS 'archived'")


def downgrade() -> None:
    # PostgreSQL tidak mendukung menghapus value dari enum secara langsung.
    pass
