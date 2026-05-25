"""SRS v1.1.0 方案 A：指数成分股权重 + 成分股日频估值

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, name: str) -> bool:
    return bool(conn.execute(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": name},
    ).fetchone())


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, "index_constituent"):
        op.create_table(
            "index_constituent",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("index_id", sa.Integer, sa.ForeignKey("index_meta.id"), nullable=False),
            sa.Column("date", sa.String(10), nullable=False),
            sa.Column("stock_code", sa.String(16), nullable=False),
            sa.Column("weight", sa.Numeric(8, 4), nullable=False),
            sa.Column("created_at", sa.String(32), nullable=False),
            sa.UniqueConstraint("index_id", "date", "stock_code"),
        )
        op.create_index("idx_constituent_index_date", "index_constituent", ["index_id", "date"])

    if not _has_table(conn, "index_constituent_quote"):
        op.create_table(
            "index_constituent_quote",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("stock_code", sa.String(16), nullable=False),
            sa.Column("date", sa.String(10), nullable=False),
            sa.Column("total_mv", sa.Numeric(20, 4)),
            sa.Column("pe_ttm", sa.Numeric(18, 6)),
            sa.Column("pb", sa.Numeric(18, 6)),
            sa.Column("source", sa.String(16), nullable=False),
            sa.Column("created_at", sa.String(32), nullable=False),
            sa.UniqueConstraint("stock_code", "date"),
        )
        op.create_index("idx_const_quote_stock_date", "index_constituent_quote", ["stock_code", "date"])


def downgrade() -> None:
    op.drop_index("idx_const_quote_stock_date", table_name="index_constituent_quote")
    op.drop_table("index_constituent_quote")
    op.drop_index("idx_constituent_index_date", table_name="index_constituent")
    op.drop_table("index_constituent")
