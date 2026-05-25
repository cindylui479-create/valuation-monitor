"""SRS v1.3.0 K：全市场证券目录（autocomplete 用）。

不绑业务（仅用于搜索建议）；周期性 seed 自 Tushare stock_basic + akshare fund_em。
"""
from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SecurityCatalog(Base):
    __tablename__ = "security_catalog"
    __table_args__ = (
        UniqueConstraint("entity_type", "code"),
        Index("idx_catalog_name", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(8))      # STOCK / FUND
    code: Mapped[str] = mapped_column(String(32))            # 600519.SH / 005827
    name: Mapped[str] = mapped_column(String(128))
    market: Mapped[str | None] = mapped_column(String(8))    # A
    extra: Mapped[str | None] = mapped_column(String(64))    # 行业 / 基金类型
    updated_at: Mapped[str] = mapped_column(String(32))
