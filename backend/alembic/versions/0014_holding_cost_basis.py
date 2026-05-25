"""SRS v1.3.0 A：Holding 加 cost_basis 列

支持记录持仓成本（用户录入）；GET 时返回 unrealized_pnl = market_value - cost_basis。

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, col: str) -> bool:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == col for r in rows)


def upgrade() -> None:
    if not _has_column(op.get_bind(), "holding", "cost_basis"):
        op.add_column("holding", sa.Column("cost_basis", sa.Numeric(18, 2)))


def downgrade() -> None:
    op.drop_column("holding", "cost_basis")
