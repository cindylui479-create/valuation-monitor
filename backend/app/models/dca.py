from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DCAPlan(Base):
    __tablename__ = "dca_plan"
    __table_args__ = (Index("idx_dca_index", "index_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"))
    fund_id: Mapped[int | None] = mapped_column(ForeignKey("fund.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    frequency: Mapped[str] = mapped_column(String(16))          # WEEKLY / BIWEEKLY / MONTHLY
    day_of_period: Mapped[int] = mapped_column(Integer)         # 1-7 周 / 1-28 月
    start_date: Mapped[str] = mapped_column(String(10))
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[str] = mapped_column(String(32))


class DCAExecution(Base):
    __tablename__ = "dca_execution"
    __table_args__ = (
        UniqueConstraint("plan_id", "actual_date"),
        Index("idx_dca_exec_plan_date", "plan_id", "actual_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("dca_plan.id"))
    scheduled_date: Mapped[str] = mapped_column(String(10))
    actual_date: Mapped[str] = mapped_column(String(10))
    base_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    adjusted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    multiplier: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    tier_at_decision: Mapped[str] = mapped_column(String(16))
    temperature: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    status: Mapped[str] = mapped_column(String(16))             # PENDING / DONE / SKIPPED
    generated_at: Mapped[str] = mapped_column(String(32))
    marked_at: Mapped[str | None] = mapped_column(String(32))
