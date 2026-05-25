"""SRS v1.2.0：Holding 加 quantity 列

支持按"股数 / 份数"录入；GET 时 market_value = quantity × latest_close。

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, col: str) -> bool:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == col for r in rows)


def upgrade() -> None:
    if not _has_column(op.get_bind(), "holding", "quantity"):
        op.add_column("holding", sa.Column("quantity", sa.Numeric(18, 4)))


def downgrade() -> None:
    op.drop_column("holding", "quantity")
