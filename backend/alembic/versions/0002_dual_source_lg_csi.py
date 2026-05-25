"""SRS R10：双口径（LG / CSI）并存

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, col: str) -> bool:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == col for r in rows)


def upgrade() -> None:
    conn = op.get_bind()

    # index_quote 加双口径列（幂等：上次失败可能已部分跑过）
    with op.batch_alter_table("index_quote") as bop:
        if not _has_column(conn, "index_quote", "pe_ttm_csi"):
            bop.add_column(sa.Column("pe_ttm_csi", sa.Numeric(18, 6), nullable=True))
        if not _has_column(conn, "index_quote", "pb_csi"):
            bop.add_column(sa.Column("pb_csi", sa.Numeric(18, 6), nullable=True))

    # valuation：batch 模式下重新创建表，加 source 列 + 新唯一约束。
    # 在 batch 里 SQLAlchemy 会把表数据迁到新表，原数据 source 自动填 server_default
    if not _has_column(conn, "valuation", "source"):
        with op.batch_alter_table(
            "valuation",
            table_args=(
                sa.UniqueConstraint(
                    "index_id", "date", "window", "source",
                    name="uq_valuation_index_date_window_source",
                ),
            ),
        ) as bop:
            bop.add_column(sa.Column("source", sa.String(8), nullable=False, server_default="lg"))


def downgrade() -> None:
    with op.batch_alter_table(
        "valuation",
        table_args=(
            sa.UniqueConstraint(
                "index_id", "date", "window",
                name="uq_valuation_index_date_window",
            ),
        ),
    ) as bop:
        bop.drop_column("source")

    with op.batch_alter_table("index_quote") as bop:
        bop.drop_column("pe_ttm_csi")
        bop.drop_column("pb_csi")
