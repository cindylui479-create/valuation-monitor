"""SRS R12 M6-A：Watchlist 扩展 entity_type + stock_id 列

旧 schema：(index_id NOT NULL, tag) 唯一
新 schema：(index_id nullable, stock_id nullable, tag, entity_type='INDEX'/'STOCK'/'FUND')
          唯一约束 (index_id, stock_id, tag)

SQLite 不支持直接 drop UNIQUE 约束，本迁移用经典「重建表」手法。

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, col: str) -> bool:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == col for r in rows)


def upgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "watchlist", "stock_id"):
        return  # 幂等：已迁移

    # 1) 新建临时表（目标 schema）
    conn.execute(sa.text("""
        CREATE TABLE watchlist_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type VARCHAR(8) NOT NULL DEFAULT 'INDEX',
            index_id INTEGER,
            stock_id INTEGER,
            tag VARCHAR(32),
            added_at VARCHAR(32) NOT NULL,
            FOREIGN KEY (index_id) REFERENCES index_meta(id),
            FOREIGN KEY (stock_id) REFERENCES stock(id),
            CONSTRAINT uq_watchlist_entity_tag UNIQUE (index_id, stock_id, tag)
        )
    """))
    # 2) 复制现有数据 — 全部是 INDEX 类型
    conn.execute(sa.text("""
        INSERT INTO watchlist_new (id, entity_type, index_id, stock_id, tag, added_at)
        SELECT id, 'INDEX', index_id, NULL, tag, added_at FROM watchlist
    """))
    # 3) 替换
    conn.execute(sa.text("DROP TABLE watchlist"))
    conn.execute(sa.text("ALTER TABLE watchlist_new RENAME TO watchlist"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        CREATE TABLE watchlist_old (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            index_id INTEGER NOT NULL,
            tag VARCHAR(32),
            added_at VARCHAR(32) NOT NULL,
            FOREIGN KEY (index_id) REFERENCES index_meta(id),
            UNIQUE (index_id, tag)
        )
    """))
    conn.execute(sa.text("""
        INSERT INTO watchlist_old (id, index_id, tag, added_at)
        SELECT id, index_id, tag, added_at FROM watchlist
        WHERE entity_type='INDEX'
    """))
    conn.execute(sa.text("DROP TABLE watchlist"))
    conn.execute(sa.text("ALTER TABLE watchlist_old RENAME TO watchlist"))
