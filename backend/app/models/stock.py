"""SRS R12 §11.2.1：个股实体模型。

Stock           — 自选个股池
StockQuote      — 个股日频行情 + 估值原始字段
StockValuation  — 个股派生分位 + 温度 + 档位
StockOverride   — 个股覆盖默认估值锚 / 阈值
"""
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Stock(Base):
    """A 股个股自选池。"""

    __tablename__ = "stock"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)             # 600519.SH / 000001.SZ
    name: Mapped[str] = mapped_column(String(64))
    market_id: Mapped[int] = mapped_column(ForeignKey("market.id"))        # 固定 A
    sw_industry_1: Mapped[str | None] = mapped_column(String(64))          # 申万一级（M6-B 接入）
    sw_industry_2: Mapped[str | None] = mapped_column(String(64))
    sw_industry_3: Mapped[str | None] = mapped_column(String(64))
    industry_raw: Mapped[str | None] = mapped_column(String(64))           # M6-A：东方财富行业
    listing_date: Mapped[str | None] = mapped_column(String(10))
    valuation_anchor: Mapped[str] = mapped_column(String(16), default="PE")  # PE/PB/PS/PE_REVERSE/DIV_YIELD
    status: Mapped[str] = mapped_column(String(16), default="active")      # active/delisted/suspended
    enabled: Mapped[bool] = mapped_column(default=True)
    added_at: Mapped[str] = mapped_column(String(32))


class StockQuote(Base):
    """个股日频行情 + 估值原始字段。结构类比 IndexQuote。"""

    __tablename__ = "stock_quote"
    __table_args__ = (
        UniqueConstraint("stock_id", "date"),
        Index("idx_stock_quote_stock_date", "stock_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stock.id"))
    date: Mapped[str] = mapped_column(String(10))
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    pe_ttm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    pe: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))              # 静态 PE
    pb: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    ps_ttm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    ps: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))  # dv_ratio (静态)
    dv_ttm: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))          # 滚动股息率
    total_mv: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))        # 总市值（万元）
    circ_mv: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))         # 流通市值（万元）
    total_share: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))     # 总股本（万股）
    source: Mapped[str] = mapped_column(String(32))                         # tushare / akshare_em
    created_at: Mapped[str] = mapped_column(String(32))


class StockValuation(Base):
    """个股派生分位 + 温度 + 档位。"""

    __tablename__ = "stock_valuation"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", "window", "source"),
        Index("idx_stock_val_stock_date", "stock_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stock.id"))
    date: Mapped[str] = mapped_column(String(10))
    window: Mapped[str] = mapped_column(String(8))                           # 5y/10y/all
    source: Mapped[str] = mapped_column(String(8), default="tushare")
    anchor: Mapped[str] = mapped_column(String(16))                          # 实际算温度的锚
    pe_percentile: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    pb_percentile: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    ps_percentile: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    dy_percentile: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    tier: Mapped[str | None] = mapped_column(String(16))
    computed_at: Mapped[str] = mapped_column(String(32))


class StockOverride(Base):
    """SRS R12 §11.2.2：用户对个股覆盖默认估值锚 / 阈值。"""

    __tablename__ = "stock_override"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stock.id"), unique=True)
    valuation_anchor: Mapped[str | None] = mapped_column(String(16))
    boundaries_json: Mapped[str | None] = mapped_column(String(256))
    updated_at: Mapped[str] = mapped_column(String(32))
