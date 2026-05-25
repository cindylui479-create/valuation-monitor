from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Watchlist(Base):
    """SRS R12 §11.2.1：扩展支持 INDEX / STOCK / FUND 三类实体。

    一行内 `index_id` / `stock_id` 二者必填且互斥（由 entity_type 决定）。
    SQLite NULL 不参与 UNIQUE 比较，因此 (index_id, stock_id, tag) 复合唯一可同时容纳两类。
    """

    __tablename__ = "watchlist"
    __table_args__ = (
        UniqueConstraint("index_id", "stock_id", "tag", name="uq_watchlist_entity_tag"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(8), default="INDEX")     # INDEX / STOCK / FUND
    index_id: Mapped[int | None] = mapped_column(ForeignKey("index_meta.id"))
    stock_id: Mapped[int | None] = mapped_column(ForeignKey("stock.id"))
    tag: Mapped[str | None] = mapped_column(String(32))
    added_at: Mapped[str] = mapped_column(String(32))
