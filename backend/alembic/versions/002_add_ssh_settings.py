"""Add SSH settings and node ssh_user

Revision ID: 002
Revises: 001
Create Date: 2026-06-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ssh_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ssh_user", sa.String(64), nullable=False),
        sa.Column("encrypted_private_key", sa.Text(), nullable=False),
        sa.Column("key_fingerprint", sa.String(128), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.add_column("nodes", sa.Column("ssh_user", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("nodes", "ssh_user")
    op.drop_table("ssh_settings")
