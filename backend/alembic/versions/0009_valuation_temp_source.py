"""SRS R12+：Valuation 加 temperature_source / close_percentile 两列

- temperature_source: 标识温度来源（pe_10y / pe_all / price_10y / price_all / null）
- close_percentile: close 历史百分位，参考用

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, col: str) -> bool:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == col for r in rows)


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "valuation", "temperature_source"):
        op.add_column("valuation", sa.Column("temperature_source", sa.String(16)))
    if not _has_column(conn, "valuation", "close_percentile"):
        op.add_column("valuation", sa.Column("close_percentile", sa.Numeric(10, 8)))


def downgrade() -> None:
    op.drop_column("valuation", "close_percentile")
    op.drop_column("valuation", "temperature_source")
