"""create agent_task_log

Revision ID: 0001
Revises:
Create Date: 2026-08-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_task_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("instruction", sa.String(2000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("agent_task_log")
