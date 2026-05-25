"""SRS R11：data_anomaly 表 — 数据异常检测落库

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
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
    if _has_table(conn, "data_anomaly"):
        return
    op.create_table(
        "data_anomaly",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("index_id", sa.Integer, sa.ForeignKey("index_meta.id"), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("field", sa.String(16), nullable=False),
        sa.Column("source", sa.String(8), nullable=False),
        sa.Column("anomaly_type", sa.String(24), nullable=False),
        sa.Column("severity", sa.String(8), nullable=False),
        sa.Column("value", sa.Numeric(18, 6)),
        sa.Column("baseline", sa.Numeric(18, 6)),
        sa.Column("note", sa.String(255)),
        sa.Column("detected_at", sa.String(32), nullable=False),
        sa.UniqueConstraint(
            "index_id", "date", "field", "source", "anomaly_type",
            name="uq_anomaly_dim",
        ),
    )
    op.create_index("idx_anomaly_index_date", "data_anomaly", ["index_id", "date"])
    op.create_index("idx_anomaly_severity_date", "data_anomaly", ["severity", "date"])


def downgrade() -> None:
    op.drop_index("idx_anomaly_severity_date", table_name="data_anomaly")
    op.drop_index("idx_anomaly_index_date", table_name="data_anomaly")
    op.drop_table("data_anomaly")
