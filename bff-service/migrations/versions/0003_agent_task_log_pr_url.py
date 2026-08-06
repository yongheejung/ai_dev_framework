"""add git connector fields to agent_task_log

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_task_log", sa.Column("pr_url", sa.String(500), nullable=True))
    op.add_column("agent_task_log", sa.Column("git_connector_error", sa.String(2000), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_task_log", "git_connector_error")
    op.drop_column("agent_task_log", "pr_url")
