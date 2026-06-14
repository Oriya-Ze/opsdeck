"""Initial schema

Revision ID: 005
Revises: 004
Create Date: 2026-06-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backup_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("auto_backup_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("backup_interval_seconds", sa.Integer(), nullable=False, server_default="86400"),
        sa.Column("last_auto_backup_at", sa.DateTime(), nullable=True),
        sa.Column("last_auto_backup_summary", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "node_backups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_type", sa.String(20), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="completed"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_node_backups_node_id", "node_backups", ["node_id"])
    op.add_column(
        "nodes",
        sa.Column("auto_backup_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("nodes", "auto_backup_enabled")
    op.drop_index("ix_node_backups_node_id", table_name="node_backups")
    op.drop_table("node_backups")
    op.drop_table("backup_settings")
