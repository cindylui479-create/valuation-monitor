"""SRS R12 §11.3.2 M7-B：场外主动基金 NAV 历史 + 派生分位。"""
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FundNAV(Base):
    """场外主动基金日频净值。ETF / 场外指数基金不入此表（走 IndexQuote 路径）。"""

    __tablename__ = "fund_nav"
    __table_args__ = (
        UniqueConstraint("fund_id", "date"),
        Index("idx_fund_nav_fund_date", "fund_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("fund.id"))
    date: Mapped[str] = mapped_column(String(10))
    nav: Mapped[Decimal] = mapped_column(Numeric(18, 6))                       # 单位净值
    accumulated_nav: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))    # 累计净值（可选）
    created_at: Mapped[str] = mapped_column(String(32))


class FundValuation(Base):
    """主动基金派生分位 + 温度。"""

    __tablename__ = "fund_valuation"
    __table_args__ = (
        UniqueConstraint("fund_id", "date", "window"),
        Index("idx_fund_val_fund_date", "fund_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("fund.id"))
    date: Mapped[str] = mapped_column(String(10))
    window: Mapped[str] = mapped_column(String(8))                              # 5y / all
    nav_percentile: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    tier: Mapped[str | None] = mapped_column(String(16))
    computed_at: Mapped[str] = mapped_column(String(32))
