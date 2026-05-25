"""SRS R12 M7-B：Fund 扩展 + 新建 FundNAV / FundValuation

- Fund 加 fund_type / setup_date / fund_manager / enabled 列
- tracks_index_id 改 nullable（ACTIVE_FUND 无跟踪指数）
- 现有 36 只基金回填 fund_type：type='ETF' → 'ETF'；type='OPEN_FUND' → 'INDEX_FUND'
- 新建 fund_nav 表（主动基金日频 NAV）
- 新建 fund_valuation 表（主动基金派生分位）

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, col: str) -> bool:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == col for r in rows)


def _has_table(conn, name: str) -> bool:
    return bool(conn.execute(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": name},
    ).fetchone())


def upgrade() -> None:
    conn = op.get_bind()

    # --- 1) Fund 加列（幂等）---
    if not _has_column(conn, "fund", "fund_type"):
        op.add_column("fund", sa.Column(
            "fund_type", sa.String(16), nullable=False, server_default="ETF",
        ))
    if not _has_column(conn, "fund", "setup_date"):
        op.add_column("fund", sa.Column("setup_date", sa.String(10)))
    if not _has_column(conn, "fund", "fund_manager"):
        op.add_column("fund", sa.Column("fund_manager", sa.String(64)))
    if not _has_column(conn, "fund", "enabled"):
        op.add_column("fund", sa.Column(
            "enabled", sa.Boolean, nullable=False, server_default=sa.text("1"),
        ))

    # 回填 fund_type：现有 OPEN_FUND 全是指数联接基金 → INDEX_FUND；ETF 保持
    conn.execute(sa.text(
        "UPDATE fund SET fund_type='INDEX_FUND' WHERE type='OPEN_FUND' AND fund_type='ETF'"
    ))

    # --- 2) tracks_index_id 改 nullable（ACTIVE_FUND 时为空）---
    # SQLite 修改列只能重建表。但因为只是改 nullable，且 SQLite 默认所有 INTEGER 列允许 NULL（除非 PK 或 NOT NULL），
    # 我们检查现有约束。当前 fund.tracks_index_id 在 0001 中是 NOT NULL，需要重建。
    if not _has_column(conn, "fund", "_tracks_nullable_marker"):
        # 用临时表迁移
        info = conn.execute(sa.text("PRAGMA table_info('fund')")).fetchall()
        tracks_row = next((r for r in info if r[1] == "tracks_index_id"), None)
        if tracks_row and tracks_row[3] == 1:  # notnull=1 需要重建
            conn.execute(sa.text("""
                CREATE TABLE fund_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code VARCHAR(32) NOT NULL UNIQUE,
                    name VARCHAR(128) NOT NULL,
                    type VARCHAR(16) NOT NULL,
                    fund_type VARCHAR(16) NOT NULL DEFAULT 'ETF',
                    tracks_index_id INTEGER,
                    market_id INTEGER NOT NULL,
                    fee_rate NUMERIC(8,6),
                    tracking_error_note VARCHAR(256),
                    setup_date VARCHAR(10),
                    fund_manager VARCHAR(64),
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    FOREIGN KEY (tracks_index_id) REFERENCES index_meta(id),
                    FOREIGN KEY (market_id) REFERENCES market(id)
                )
            """))
            conn.execute(sa.text("""
                INSERT INTO fund_new (id, code, name, type, fund_type, tracks_index_id,
                                      market_id, fee_rate, tracking_error_note, setup_date,
                                      fund_manager, enabled)
                SELECT id, code, name, type, fund_type, tracks_index_id,
                       market_id, fee_rate, tracking_error_note, setup_date,
                       fund_manager, enabled FROM fund
            """))
            conn.execute(sa.text("DROP TABLE fund"))
            conn.execute(sa.text("ALTER TABLE fund_new RENAME TO fund"))
            conn.execute(sa.text(
                "CREATE INDEX IF NOT EXISTS idx_fund_tracks ON fund(tracks_index_id)"
            ))

    # --- 3) 新表 fund_nav / fund_valuation ---
    if not _has_table(conn, "fund_nav"):
        op.create_table(
            "fund_nav",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("fund_id", sa.Integer, sa.ForeignKey("fund.id"), nullable=False),
            sa.Column("date", sa.String(10), nullable=False),
            sa.Column("nav", sa.Numeric(18, 6), nullable=False),
            sa.Column("accumulated_nav", sa.Numeric(18, 6)),
            sa.Column("created_at", sa.String(32), nullable=False),
            sa.UniqueConstraint("fund_id", "date"),
        )
        op.create_index("idx_fund_nav_fund_date", "fund_nav", ["fund_id", "date"])

    if not _has_table(conn, "fund_valuation"):
        op.create_table(
            "fund_valuation",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("fund_id", sa.Integer, sa.ForeignKey("fund.id"), nullable=False),
            sa.Column("date", sa.String(10), nullable=False),
            sa.Column("window", sa.String(8), nullable=False),
            sa.Column("nav_percentile", sa.Numeric(18, 8)),
            sa.Column("temperature", sa.Numeric(18, 4)),
            sa.Column("tier", sa.String(16)),
            sa.Column("computed_at", sa.String(32), nullable=False),
            sa.UniqueConstraint("fund_id", "date", "window"),
        )
        op.create_index("idx_fund_val_fund_date", "fund_valuation", ["fund_id", "date"])


def downgrade() -> None:
    op.drop_index("idx_fund_val_fund_date", table_name="fund_valuation")
    op.drop_table("fund_valuation")
    op.drop_index("idx_fund_nav_fund_date", table_name="fund_nav")
    op.drop_table("fund_nav")
    # Fund 列不回滚（旧 0001 不知道这些列存在；不影响读取）
