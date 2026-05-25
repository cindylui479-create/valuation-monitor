"""SRS R11：data_anomaly 加 acknowledged_at / acknowledged_note

用户人工核对过的异常可标记，UI 默认隐藏，避免每次重看时重复判断。

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, col: str) -> bool:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == col for r in rows)


def upgrade() -> None:
    conn = op.get_bind()
    with op.batch_alter_table("data_anomaly") as bop:
        if not _has_column(conn, "data_anomaly", "acknowledged_at"):
            bop.add_column(sa.Column("acknowledged_at", sa.String(32), nullable=True))
        if not _has_column(conn, "data_anomaly", "acknowledged_note"):
            bop.add_column(sa.Column("acknowledged_note", sa.String(255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("data_anomaly") as bop:
        bop.drop_column("acknowledged_note")
        bop.drop_column("acknowledged_at")
