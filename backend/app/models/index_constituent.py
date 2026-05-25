"""SRS v1.1.0 方案 A：指数成分股权重 + 成分股日频估值数据。

与 `Stock` / `StockQuote`（自选个股）分离 — 这是给"指数成分股聚合 PE"用的
专用数据源，不污染自选池。
"""
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IndexConstituent(Base):
    """指数月度成分股 + 权重（Tushare index_weight 接口）。

    每月报告一次（中证一般月底）；同一 (index, date, stock_code) 唯一。
    日频回算时对每个日期取 ≤ 该日的最新月度权重（forward-fill）。
    """

    __tablename__ = "index_constituent"
    __table_args__ = (
        UniqueConstraint("index_id", "date", "stock_code"),
        Index("idx_constituent_index_date", "index_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"))
    date: Mapped[str] = mapped_column(String(10))                       # 月度报告日
    stock_code: Mapped[str] = mapped_column(String(16))                 # 600519.SH
    weight: Mapped[Decimal] = mapped_column(Numeric(8, 4))              # %（如 9.87）
    created_at: Mapped[str] = mapped_column(String(32))


class IndexConstituentQuote(Base):
    """成分股日频 mv + pe_ttm（Tushare daily_basic 接口）。

    专为整体法聚合 PE 服务；与 `StockQuote`（自选个股）逻辑独立。
    """

    __tablename__ = "index_constituent_quote"
    __table_args__ = (
        UniqueConstraint("stock_code", "date"),
        Index("idx_const_quote_stock_date", "stock_code", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16))                 # 主键来源；不 FK 到 stock.id 因为自选与成分股集合不同
    date: Mapped[str] = mapped_column(String(10))
    total_mv: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))    # 万元
    pe_ttm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    pb: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    source: Mapped[str] = mapped_column(String(16))                     # 'tushare'
    created_at: Mapped[str] = mapped_column(String(32))
