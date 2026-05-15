"""init extensions and per-domain schemas

Revision ID: 0001_init
Revises:
Create Date: 2026-05-15

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMAS = (
    "core",
    "memory",
    "schedule",
    "ledger",
    "finance",
    "ideas",
    "files",
    "todo",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    for schema in SCHEMAS:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')


def downgrade() -> None:
    for schema in reversed(SCHEMAS):
        op.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
    op.execute("DROP EXTENSION IF EXISTS vector")
