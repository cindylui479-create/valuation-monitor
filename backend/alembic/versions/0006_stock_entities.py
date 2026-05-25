"""SRS R12 M6-A：新建个股实体表（Stock / StockQuote / StockValuation / StockOverride）

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, name: str) -> bool:
    rows = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": name},
    ).fetchall()
    return bool(rows)


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, "stock"):
        op.create_table(
            "stock",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("code", sa.String(16), nullable=False, unique=True),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("market_id", sa.Integer, sa.ForeignKey("market.id"), nullable=False),
            sa.Column("sw_industry_1", sa.String(64)),
            sa.Column("sw_industry_2", sa.String(64)),
            sa.Column("sw_industry_3", sa.String(64)),
            sa.Column("industry_raw", sa.String(64)),
            sa.Column("listing_date", sa.String(10)),
            sa.Column("valuation_anchor", sa.String(16), nullable=False, server_default="PE"),
            sa.Column("status", sa.String(16), nullable=False, server_default="active"),
            sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("1")),
            sa.Column("added_at", sa.String(32), nullable=False),
        )

    if not _has_table(conn, "stock_quote"):
        op.create_table(
            "stock_quote",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("stock_id", sa.Integer, sa.ForeignKey("stock.id"), nullable=False),
            sa.Column("date", sa.String(10), nullable=False),
            sa.Column("close", sa.Numeric(18, 6), nullable=False),
            sa.Column("pe_ttm", sa.Numeric(18, 6)),
            sa.Column("pe", sa.Numeric(18, 6)),
            sa.Column("pb", sa.Numeric(18, 6)),
            sa.Column("ps_ttm", sa.Numeric(18, 6)),
            sa.Column("ps", sa.Numeric(18, 6)),
            sa.Column("dividend_yield", sa.Numeric(18, 8)),
            sa.Column("dv_ttm", sa.Numeric(18, 8)),
            sa.Column("total_mv", sa.Numeric(20, 4)),
            sa.Column("circ_mv", sa.Numeric(20, 4)),
            sa.Column("total_share", sa.Numeric(20, 4)),
            sa.Column("source", sa.String(32), nullable=False),
            sa.Column("created_at", sa.String(32), nullable=False),
            sa.UniqueConstraint("stock_id", "date"),
        )
        op.create_index("idx_stock_quote_stock_date", "stock_quote", ["stock_id", "date"])

    if not _has_table(conn, "stock_valuation"):
        op.create_table(
            "stock_valuation",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("stock_id", sa.Integer, sa.ForeignKey("stock.id"), nullable=False),
            sa.Column("date", sa.String(10), nullable=False),
            sa.Column("window", sa.String(8), nullable=False),
            sa.Column("source", sa.String(8), nullable=False, server_default="tushare"),
            sa.Column("anchor", sa.String(16), nullable=False),
            sa.Column("pe_percentile", sa.Numeric(18, 8)),
            sa.Column("pb_percentile", sa.Numeric(18, 8)),
            sa.Column("ps_percentile", sa.Numeric(18, 8)),
            sa.Column("dy_percentile", sa.Numeric(18, 8)),
            sa.Column("temperature", sa.Numeric(18, 4)),
            sa.Column("tier", sa.String(16)),
            sa.Column("computed_at", sa.String(32), nullable=False),
            sa.UniqueConstraint("stock_id", "date", "window", "source"),
        )
        op.create_index("idx_stock_val_stock_date", "stock_valuation", ["stock_id", "date"])

    if not _has_table(conn, "stock_override"):
        op.create_table(
            "stock_override",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("stock_id", sa.Integer, sa.ForeignKey("stock.id"), nullable=False, unique=True),
            sa.Column("valuation_anchor", sa.String(16)),
            sa.Column("boundaries_json", sa.String(256)),
            sa.Column("updated_at", sa.String(32), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("stock_override")
    op.drop_index("idx_stock_val_stock_date", table_name="stock_valuation")
    op.drop_table("stock_valuation")
    op.drop_index("idx_stock_quote_stock_date", table_name="stock_quote")
    op.drop_table("stock_quote")
    op.drop_table("stock")
