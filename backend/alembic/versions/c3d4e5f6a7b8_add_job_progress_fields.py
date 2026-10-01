"""add job progress fields

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-01 11:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "processing_jobs",
        sa.Column("stage", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("processing_jobs", "progress_percent", server_default=None)


def downgrade() -> None:
    op.drop_column("processing_jobs", "progress_percent")
    op.drop_column("processing_jobs", "stage")
