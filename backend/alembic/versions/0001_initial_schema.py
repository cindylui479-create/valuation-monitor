"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(8), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("tz", sa.String(64), nullable=False),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "trading_calendar",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("market_id", sa.Integer, sa.ForeignKey("market.id"), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("is_open", sa.Boolean, nullable=False),
        sa.UniqueConstraint("market_id", "date"),
    )
    op.create_index("idx_calendar_market_date", "trading_calendar", ["market_id", "date"])

    op.create_table(
        "index_meta",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("market_id", sa.Integer, sa.ForeignKey("market.id"), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("industry_raw", sa.String(64)),
        sa.Column("data_source", sa.String(32), nullable=False),
        sa.Column("history_start_date", sa.String(10), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "fund",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("tracks_index_id", sa.Integer, sa.ForeignKey("index_meta.id"), nullable=False),
        sa.Column("market_id", sa.Integer, sa.ForeignKey("market.id"), nullable=False),
        sa.Column("fee_rate", sa.Numeric(8, 6)),
        sa.Column("tracking_error_note", sa.String(256)),
        sa.UniqueConstraint("code"),
    )
    op.create_index("idx_fund_tracks", "fund", ["tracks_index_id"])

    op.create_table(
        "index_quote",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("index_id", sa.Integer, sa.ForeignKey("index_meta.id"), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("close", sa.Numeric(18, 6), nullable=False),
        sa.Column("pe_ttm", sa.Numeric(18, 6)),
        sa.Column("pb", sa.Numeric(18, 6)),
        sa.Column("dividend_yield", sa.Numeric(18, 8)),
        sa.Column("roe", sa.Numeric(18, 8)),
        sa.Column("earnings_growth_3y", sa.Numeric(18, 8)),
        sa.Column("ma50", sa.Numeric(18, 6)),
        sa.Column("ma200", sa.Numeric(18, 6)),
        sa.Column("northbound_60d_pct", sa.Numeric(18, 8)),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.UniqueConstraint("index_id", "date"),
    )
    op.create_index("idx_quote_index_date", "index_quote", ["index_id", "date"])

    op.create_table(
        "valuation",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("index_id", sa.Integer, sa.ForeignKey("index_meta.id"), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("window", sa.String(8), nullable=False),
        sa.Column("pe_percentile", sa.Numeric(10, 8)),
        sa.Column("pb_percentile", sa.Numeric(10, 8)),
        sa.Column("dy_percentile", sa.Numeric(10, 8)),
        sa.Column("temperature", sa.Numeric(10, 6)),
        sa.Column("tier", sa.String(16)),
        sa.Column("computed_at", sa.String(32), nullable=False),
        sa.UniqueConstraint("index_id", "date", "window"),
    )
    op.create_index("idx_valuation_index_date_window", "valuation", ["index_id", "date", "window"])

    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("index_id", sa.Integer, sa.ForeignKey("index_meta.id"), nullable=False),
        sa.Column("tag", sa.String(32)),
        sa.Column("added_at", sa.String(32), nullable=False),
        sa.UniqueConstraint("index_id", "tag"),
    )

    op.create_table(
        "signal",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("index_id", sa.Integer, sa.ForeignKey("index_meta.id"), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("tier", sa.String(16), nullable=False),
        sa.Column("temperature", sa.Numeric(10, 6), nullable=False),
        sa.Column("generated_at", sa.String(32), nullable=False),
        sa.UniqueConstraint("index_id", "date"),
    )
    op.create_index("idx_signal_date", "signal", ["date"])

    op.create_table(
        "dca_plan",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("index_id", sa.Integer, sa.ForeignKey("index_meta.id"), nullable=False),
        sa.Column("fund_id", sa.Integer, sa.ForeignKey("fund.id")),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("frequency", sa.String(16), nullable=False),
        sa.Column("day_of_period", sa.Integer, nullable=False),
        sa.Column("start_date", sa.String(10), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    )
    op.create_index("idx_dca_index", "dca_plan", ["index_id"])

    op.create_table(
        "dca_execution",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("plan_id", sa.Integer, sa.ForeignKey("dca_plan.id"), nullable=False),
        sa.Column("scheduled_date", sa.String(10), nullable=False),
        sa.Column("actual_date", sa.String(10), nullable=False),
        sa.Column("base_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("adjusted_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("multiplier", sa.Numeric(6, 2), nullable=False),
        sa.Column("tier_at_decision", sa.String(16), nullable=False),
        sa.Column("temperature", sa.Numeric(10, 6), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("generated_at", sa.String(32), nullable=False),
        sa.Column("marked_at", sa.String(32)),
        sa.UniqueConstraint("plan_id", "actual_date"),
    )
    op.create_index("idx_dca_exec_plan_date", "dca_execution", ["plan_id", "actual_date"])

    op.create_table(
        "threshold_override",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("index_id", sa.Integer, sa.ForeignKey("index_meta.id"), nullable=False),
        sa.Column("boundaries_json", sa.String(512), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.UniqueConstraint("index_id"),
    )

    op.create_table(
        "data_audit",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("table_name", sa.String(32), nullable=False),
        sa.Column("record_key", sa.String(128), nullable=False),
        sa.Column("field", sa.String(32), nullable=False),
        sa.Column("old_value", sa.String(64)),
        sa.Column("new_value", sa.String(64)),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("audit_time", sa.String(32), nullable=False),
    )
    op.create_index("idx_audit_record", "data_audit", ["record_key"])

    op.create_table(
        "user_preference",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("value_json", sa.String(2048), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.UniqueConstraint("key"),
    )


def downgrade() -> None:
    for tbl in [
        "user_preference",
        "data_audit",
        "threshold_override",
        "dca_execution",
        "dca_plan",
        "signal",
        "watchlist",
        "valuation",
        "index_quote",
        "fund",
        "index_meta",
        "trading_calendar",
        "market",
    ]:
        op.drop_table(tbl)
