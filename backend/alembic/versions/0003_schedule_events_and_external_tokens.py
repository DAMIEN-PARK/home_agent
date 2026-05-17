"""schedule.events table and core.users.external_tokens column

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002_core_memory_todo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("external_tokens", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="core",
    )

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(16), nullable=False, server_default="local"),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["core.users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("source", "external_id", name="uq_events_source_external"),
        schema="schedule",
    )
    op.create_index(
        "ix_schedule_events_user_start",
        "events",
        ["user_id", "start_at"],
        schema="schedule",
    )


def downgrade() -> None:
    op.drop_index("ix_schedule_events_user_start", table_name="events", schema="schedule")
    op.drop_table("events", schema="schedule")
    op.drop_column("users", "external_tokens", schema="core")
