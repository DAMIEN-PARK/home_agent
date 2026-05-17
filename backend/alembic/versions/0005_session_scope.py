"""core.sessions: add scope (orchestrator / schedule / todo / ledger / finance / ideas / files)

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "scope",
            sa.String(32),
            nullable=False,
            server_default="orchestrator",
        ),
        schema="core",
    )
    op.create_index(
        "ix_core_sessions_device_scope",
        "sessions",
        ["device_id", "scope"],
        schema="core",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_core_sessions_device_scope", table_name="sessions", schema="core"
    )
    op.drop_column("sessions", "scope", schema="core")
