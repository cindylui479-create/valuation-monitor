"""SRS v1.3.0 K：security_catalog 表（全市场搜索目录）

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, name: str) -> bool:
    return bool(conn.execute(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": name},
    ).fetchone())


def upgrade() -> None:
    if _has_table(op.get_bind(), "security_catalog"):
        return
    op.create_table(
        "security_catalog",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entity_type", sa.String(8), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("market", sa.String(8)),
        sa.Column("extra", sa.String(64)),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.UniqueConstraint("entity_type", "code"),
    )
    op.create_index("idx_catalog_name", "security_catalog", ["name"])


def downgrade() -> None:
    op.drop_index("idx_catalog_name", table_name="security_catalog")
    op.drop_table("security_catalog")
