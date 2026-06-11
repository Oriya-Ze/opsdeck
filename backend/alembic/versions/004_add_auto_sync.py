"""Add auto-sync settings and per-node container sync flag

Revision ID: 004
Revises: 003
Create Date: 2026-06-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sync_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("containers_auto_sync_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("containers_sync_interval_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("last_auto_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_auto_sync_summary", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.add_column(
        "nodes",
        sa.Column("auto_sync_containers", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("nodes", "auto_sync_containers")
    op.drop_table("sync_settings")
