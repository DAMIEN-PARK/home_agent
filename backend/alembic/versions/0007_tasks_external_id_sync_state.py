"""todo.tasks gets source/external_id/synced_at/sync_state/retry_count for Todoist sync

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("source", sa.String(16), nullable=False, server_default="local"),
        schema="todo",
    )
    op.add_column(
        "tasks",
        sa.Column("external_id", sa.String(255), nullable=True),
        schema="todo",
    )
    op.add_column(
        "tasks",
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        schema="todo",
    )
    op.add_column(
        "tasks",
        sa.Column("sync_state", sa.String(16), nullable=True),
        schema="todo",
    )
    op.add_column(
        "tasks",
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        schema="todo",
    )
    op.create_unique_constraint(
        "uq_tasks_source_external",
        "tasks",
        ["source", "external_id"],
        schema="todo",
    )
    op.create_index(
        "ix_todo_tasks_sync_state",
        "tasks",
        ["sync_state"],
        schema="todo",
    )


def downgrade() -> None:
    op.drop_index("ix_todo_tasks_sync_state", table_name="tasks", schema="todo")
    op.drop_constraint("uq_tasks_source_external", "tasks", schema="todo", type_="unique")
    op.drop_column("tasks", "retry_count", schema="todo")
    op.drop_column("tasks", "sync_state", schema="todo")
    op.drop_column("tasks", "synced_at", schema="todo")
    op.drop_column("tasks", "external_id", schema="todo")
    op.drop_column("tasks", "source", schema="todo")
