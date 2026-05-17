"""core.sessions: add device_id, device_name (LAN device scoping)

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="core",
    )
    op.add_column(
        "sessions",
        sa.Column("device_name", sa.String(120), nullable=True),
        schema="core",
    )
    op.create_index(
        "ix_core_sessions_device_id",
        "sessions",
        ["device_id"],
        schema="core",
    )


def downgrade() -> None:
    op.drop_index("ix_core_sessions_device_id", table_name="sessions", schema="core")
    op.drop_column("sessions", "device_name", schema="core")
    op.drop_column("sessions", "device_id", schema="core")
