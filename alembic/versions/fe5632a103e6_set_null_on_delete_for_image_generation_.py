"""set null on delete for image_generation_logs task_id

Revision ID: fe5632a103e6
Revises: 798df3a8e531
Create Date: 2026-07-19 06:39:38.582217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe5632a103e6'
down_revision: Union[str, None] = '798df3a8e531'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "image_generation_logs_task_id_fkey",
        "image_generation_logs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "image_generation_logs_task_id_fkey",
        "image_generation_logs",
        "tasks",
        ["task_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "image_generation_logs_task_id_fkey",
        "image_generation_logs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "image_generation_logs_task_id_fkey",
        "image_generation_logs",
        "tasks",
        ["task_id"],
        ["id"],
    )
