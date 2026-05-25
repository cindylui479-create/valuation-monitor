"""SRS R10：signal 表加 source 列，双口径信号并存

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, col: str) -> bool:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == col for r in rows)


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "signal", "source"):
        with op.batch_alter_table("signal") as bop:
            bop.add_column(sa.Column("source", sa.String(8), nullable=False, server_default="lg"))


def downgrade() -> None:
    with op.batch_alter_table("signal") as bop:
        bop.drop_column("source")
