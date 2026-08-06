"""add orchestrator delegation fields to agent_task_log

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_task_log", sa.Column("job_id", sa.String(36), nullable=True))
    op.add_column("agent_task_log", sa.Column("run_id", sa.String(36), nullable=True))
    op.add_column("agent_task_log", sa.Column("delegation_error", sa.String(2000), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_task_log", "delegation_error")
    op.drop_column("agent_task_log", "run_id")
    op.drop_column("agent_task_log", "job_id")
