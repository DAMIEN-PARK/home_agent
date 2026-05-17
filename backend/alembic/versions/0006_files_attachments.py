"""files.attachments table for domain-chat file uploads

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="files",
    )
    op.create_index(
        "ix_files_attachments_user", "attachments", ["user_id"], schema="files"
    )
    op.create_index(
        "ix_files_attachments_sha256", "attachments", ["sha256"], schema="files"
    )


def downgrade() -> None:
    op.drop_index("ix_files_attachments_sha256", table_name="attachments", schema="files")
    op.drop_index("ix_files_attachments_user", table_name="attachments", schema="files")
    op.drop_table("attachments", schema="files")
