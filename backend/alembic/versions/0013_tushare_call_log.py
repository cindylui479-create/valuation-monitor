"""SRS v1.3.0 E：tushare_call_log 表 — 配额监控

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, name: str) -> bool:
    return bool(conn.execute(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": name},
    ).fetchone())


def upgrade() -> None:
    if _has_table(op.get_bind(), "tushare_call_log"):
        return
    op.create_table(
        "tushare_call_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("call_date", sa.String(10), nullable=False),
        sa.Column("interface", sa.String(32), nullable=False),
        sa.Column("n_calls", sa.Integer, nullable=False, server_default="0"),
        sa.Column("n_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error_message", sa.String(255)),
        sa.Column("last_called_at", sa.String(32), nullable=False),
        sa.UniqueConstraint("call_date", "interface"),
    )
    op.create_index("idx_tushare_call_date", "tushare_call_log", ["call_date"])


def downgrade() -> None:
    op.drop_index("idx_tushare_call_date", table_name="tushare_call_log")
    op.drop_table("tushare_call_log")
