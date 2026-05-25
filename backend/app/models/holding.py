"""SRS v1.2.0 S#3：用户持仓视图（不强外键，灵活录入）。

Holding 表只记录"市值"，不接成本基/盈亏 — MVP 简化。
"""
from decimal import Decimal

from sqlalchemy import Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Holding(Base):
    """单只持仓项。

    entity_type 决定查温度的途径：
      INDEX → Valuation (10y, lg)
      STOCK → StockValuation (10y)
      FUND → Fund.fund_type 决定（ETF/INDEX_FUND 挂跟踪指数；ACTIVE_FUND 用 FundValuation）

    market_value 由用户手工录入（人民币口径；港美股 ETF 用户自己换算）。
    """

    __tablename__ = "holding"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_code", "note"),  # 同标的不同备注允许多条
        Index("idx_holding_type", "entity_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(8))           # INDEX / STOCK / FUND
    entity_code: Mapped[str] = mapped_column(String(32))          # 000300.SH / 600519.SH / 005827
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2)) # 用户输入的当前市值（元）；quantity 非空时此字段为后端落库时的快照
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))  # 股数/份数（按数量模式录入时填）
    cost_basis: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))  # 持仓成本总额（元），可选；用于算未实现盈亏
    note: Mapped[str | None] = mapped_column(String(64))
    added_at: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[str] = mapped_column(String(32))
