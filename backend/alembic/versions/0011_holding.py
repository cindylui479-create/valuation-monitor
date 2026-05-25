"""SRS v1.2.0 S#3：Holding 表

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, name: str) -> bool:
    return bool(conn.execute(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": name},
    ).fetchone())


def upgrade() -> None:
    if _has_table(op.get_bind(), "holding"):
        return
    op.create_table(
        "holding",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entity_type", sa.String(8), nullable=False),
        sa.Column("entity_code", sa.String(32), nullable=False),
        sa.Column("market_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("note", sa.String(64)),
        sa.Column("added_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.UniqueConstraint("entity_type", "entity_code", "note", name="uq_holding_dim"),
    )
    op.create_index("idx_holding_type", "holding", ["entity_type"])


def downgrade() -> None:
    op.drop_index("idx_holding_type", table_name="holding")
    op.drop_table("holding")
